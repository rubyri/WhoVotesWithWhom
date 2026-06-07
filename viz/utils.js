// ─────────────────────────────────────────────────────────────────────────────
//  utils.js — shared utilities for country.html and story.html
// ─────────────────────────────────────────────────────────────────────────────

// ── Constants ─────────────────────────────────────────────────────────────────

export const DATA_PATHS = {
  database: "../data/processed/votes.db",
  sqlwasm:  "https://cdnjs.cloudflare.com/ajax/libs/sql.js/1.10.2/sql-wasm.wasm",
  unclean:  "../data/processed/un_clean.csv",
};

export const BLOCS = {
  EU: ["AUT","BEL","BGR","HRV","CYP","CZE","DNK","EST","FIN","FRA","DEU",
       "GRC","HUN","IRL","ITA","LVA","LTU","LUX","MLT","NLD","POL","PRT",
       "ROU","SVK","SVN","ESP","SWE"],
  NATO: ["ALB","BEL","CAN","HRV","CZE","DNK","EST","FRA","DEU","GRC","HUN",
         "ISL","ITA","LVA","LTU","LUX","MNE","NLD","MKD","NOR","POL","PRT",
         "ROU","SVK","SVN","ESP","TUR","GBR","USA"],
  BRICS: ["BRA","RUS","IND","CHN","ZAF","EGY","ETH","IRN","ARE","SAU"],
};

// Agreement color scale — shared across map, country, and story
export const colorScale = d3.scaleSequential()
  .domain([0.4, 1.0])
  .interpolator(d3.interpolateRgbBasis(["#c0392b","#e67e22","#27ae60","#1a3a6e"]));

// ── Database ──────────────────────────────────────────────────────────────────

// Global database handle — set by loadDatabase(), used by query()
export let DB = null;

/**
 * Loads and parses votes.db into memory via sql.js.
 * Shows progress in #loading-text and #loading-progress elements.
 */
export async function loadDatabase() {
  const loadingText = document.getElementById("loading-text");
  const loadingProg = document.getElementById("loading-progress");

  loadingText.textContent = "Initialising database engine";
  const SQL = await initSqlJs({ locateFile: () => DATA_PATHS.sqlwasm });

  loadingText.textContent = "Loading database";
  const response = await fetch(DATA_PATHS.database);
  const totalMB  = response.headers.get("content-length")
    ? (response.headers.get("content-length") / 1024 / 1024).toFixed(0) : "?";

  const reader = response.body.getReader();
  const chunks = [];
  let received = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    received += value.length;
    loadingProg.textContent = `${(received/1024/1024).toFixed(0)} / ${totalMB} MB`;
  }

  const buffer = new Uint8Array(received);
  let offset = 0;
  for (const chunk of chunks) { buffer.set(chunk, offset); offset += chunk.length; }

  loadingText.textContent = "Parsing database";
  loadingProg.textContent = "";
  DB = new SQL.Database(buffer);
}

// ── SQL helper ────────────────────────────────────────────────────────────────

/**
 * Runs a SQL query against the loaded database and returns rows as plain objects.
 * Uses ? placeholders for safe parameter binding.
 * Returns [] if the database hasn't loaded yet.
 */
export function query(sql, params = []) {
  if (!DB) return [];
  const stmt = DB.prepare(sql);
  stmt.bind(params);
  const rows = [];
  while (stmt.step()) rows.push(stmt.getAsObject());
  stmt.free();
  return rows;
}

// ── Country helpers ───────────────────────────────────────────────────────────

/** Returns the full country name for a given ISO3 code. Falls back to the code itself. */
export function getCountryName(code) {
  const r = query("SELECT country_name FROM countries WHERE ms_code = ?", [code]);
  return r.length ? r[0].country_name : code;
}

/** Returns the ISO2 code for a given ISO3 code, or null if not found. */
export function getIso2(code) {
  const r = query("SELECT iso2 FROM countries WHERE ms_code = ?", [code]);
  return r.length ? r[0].iso2 : null;
}

// ── Visual helpers ────────────────────────────────────────────────────────────

/**
 * Returns an <img> tag for a country flag from flagcdn.com.
 * Returns an empty string if iso2 is null.
 */
export function flagImg(iso2, name, w = 20, h = 15) {
  if (!iso2) return "";
  return `<img src="https://flagcdn.com/${w}x${h}/${iso2}.png"
               srcset="https://flagcdn.com/${w*2}x${h*2}/${iso2}.png 2x"
               style="border-radius:2px;vertical-align:middle;flex-shrink:0;"
               alt="${name}">`;
}

/** Returns an ordinal string for a number — e.g. 1 → "1st", 3 → "3rd". */
export function ordinal(n) {
  const s = ["th","st","nd","rd"];
  const v = n % 100;
  return n + (s[(v-20)%10] || s[v] || s[0]);
}

// ── DNA stripe ────────────────────────────────────────────────────────────────

/**
 * Renders the DNA stripe — one colored vertical stripe per year showing
 * average agreement score. Shared between country.html and story.html.
 * Requires a #dna-svg element and a #dna-tooltip element in the DOM.
 *
 * @param {string} msCode - ISO3 country code to render for
 */
export function renderDNA(msCode) {
  const rows = query(
    "SELECT year, consensus FROM mat_consensus_overall WHERE ms_code = ? ORDER BY year",
    [msCode]
  );
  if (!rows.length) return;

  const svg     = d3.select("#dna-svg");
  const w       = svg.node().clientWidth;
  const h       = 55;
  const barH    = 34;
  svg.attr("viewBox", `0 0 ${w} ${h}`);
  svg.selectAll("*").remove();

  const stripeW = w / rows.length;
  const tooltip = document.getElementById("dna-tooltip");

  svg.selectAll("rect.stripe")
    .data(rows)
    .join("rect")
    .attr("class","stripe")
    .attr("x",      (d, i) => i * stripeW)
    .attr("y",      0)
    .attr("width",  stripeW + 0.5)
    .attr("height", barH)
    .attr("fill",   d => colorScale(d.consensus))
    .on("mousemove", function(event, d) {
      tooltip.style.opacity = "1";
      tooltip.style.left    = (event.clientX + 12) + "px";
      tooltip.style.top     = (event.clientY - 32) + "px";
      tooltip.textContent   = `${d.year}  ·  ${(d.consensus * 100).toFixed(1)}%`;
    })
    .on("mouseleave", () => tooltip.style.opacity = "0");

  const x       = d3.scaleLinear().domain([rows[0].year, rows[rows.length-1].year]).range([0, w]);
  const decades = rows.filter(d => d.year % 10 === 0);

  svg.selectAll("line.tick").data(decades).join("line")
    .attr("class","tick")
    .attr("x1", d => x(d.year)).attr("x2", d => x(d.year))
    .attr("y1", barH).attr("y2", barH + 4)
    .attr("stroke","#9898b0").attr("stroke-width", 0.8);

  svg.selectAll("text.decade").data(decades).join("text")
    .attr("class","decade")
    .attr("x",           d => x(d.year))
    .attr("y",           barH + 14)
    .attr("text-anchor", "middle")
    .attr("font-size",   "9")
    .attr("fill",        "#9898b0")
    .attr("font-family", "Outfit,sans-serif")
    .text(d => d.year);
}