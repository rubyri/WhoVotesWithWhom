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
  NATO: ["ALB","BEL","CAN","HRV","CZE","DNK","EST","FIN","FRA","DEU","GRC","HUN",
         "ISL","ITA","LVA","LTU","LUX","MNE","NLD","MKD","NOR","POL","PRT",
         "ROU","SVK","SVN","ESP","TUR","GBR","USA","SWE"],
  BRICS: ["BRA","RUS","IND","CHN","ZAF","EGY","ETH","IRN","ARE","SAU"],
  PfP: ["AUT","IRL","CHE","MLT","CYP",
        "UKR","GEO","ARM","AZE","MDA",
        "KAZ","KGZ","TJK","TKM","UZB",
        "BIH","SRB"],
  OIC: ["AFG","ALB","DZA","AZE","BHR","BGD","BEN","BRN","BFA","CMR","TCD",
        "COM","CIV","DJI","EGY","GAB","GMB","GIN","GNB","GUY","IDN","IRN",
        "IRQ","JOR","KAZ","KWT","KGZ","LBN","LBY","MYS","MDV","MLI","MRT",
        "MAR","MOZ","NER","NGA","OMN","PAK","PSE","QAT","SAU","SEN","SLE",
        "SOM","SDN","SUR","SYR","TJK","TGO","TUN","TUR","TKM","UGA","ARE",
        "UZB","YEM"],
  "African Group": ["DZA","AGO","BEN","BWA","BFA","BDI","CPV","CMR","CAF","TCD",
                    "COM","COD","COG","CIV","DJI","EGY","GNQ","ERI","SWZ","ETH",
                    "GAB","GMB","GHA","GIN","GNB","KEN","LSO","LBR","LBY","MDG",
                    "MWI","MLI","MRT","MUS","MAR","MOZ","NAM","NER","NGA","RWA",
                    "STP","SEN","SLE","SOM","ZAF","SSD","SDN","TZA","TGO","TUN",
                    "UGA","ZMB","ZWE"],
  CELAC: ["ARG","ATG","BHS","BLZ","BOL","BRB","CHL","COL","CRI","CUB",
          "DMA","DOM","ECU","SLV","GRD","GTM","GUY","HTI","HND","JAM",
          "MEX","NIC","PAN","PRY","PER","KNA","LCA","VCT","SUR","TTO",
          "URY","VEN","BRA"],
  ASEAN: ["BRN","KHM","IDN","LAO","MYS","MMR","PHL","SGP","THA","VNM"],
};

// ── Bloc colors — Paul Tol's Muted (colorblind-safe) ──────────────────────────
export const BLOC_COLORS = {
  "EU":           "#332288",
  "NATO":         "#88CCEE",
  "BRICS":        "#44AA99",
  "PfP":          "#117733",
  "OIC":          "#999933",
  "African Group":"#DDCC77",
  "CELAC":        "#CC6677",
  "ASEAN":        "#882255",
  "Other":        "#DDDDDD",
};

// ── Bloc full names and member counts ─────────────────────────────────────────
export const BLOC_LABELS = {
  "EU":           "European Union",
  "NATO":         "North Atlantic Treaty Organization",
  "BRICS":        "BRICS",
  "PfP":          "Partnership for Peace",
  "OIC":          "Organisation of Islamic Cooperation",
  "African Group":"African Group at the UN",
  "CELAC":        "Community of Latin American and Caribbean States",
  "ASEAN":        "Association of Southeast Asian Nations",
};

// ── Defunct countries ─────────────────────────────────────────────────────────
export const DEFUNCT = {
  "CSK": { name: "Czechoslovakia",             founded: "1918", end: "1993" },
  "YUG": { name: "Yugoslavia",                  founded: "1918", end: "1992" },
  "SUN": { name: "USSR",                        founded: "1922", end: "1991" },
  "DDR": { name: "German Democratic Republic",  founded: "1949", end: "1990" },
  "GER": { name: "Germany (West)",              founded: "1949", end: "1990" },
  "SCG": { name: "Serbia and Montenegro",       founded: "2003", end: "2006" },
  "YMD": { name: "Democratic Yemen",            founded: "1967", end: "1990" },
  "EAZ": { name: "Zanzibar",                    founded: "1963", end: "1964" },
  "EAT": { name: "Tanganyika",                  founded: "1961", end: "1964" },
};

// DNA stripe color scale — Paul Tol's Sunset (colorblind-safe)
// Low agreement = warm red/orange, High = cool blue
export const colorScale = d3.scaleSequential()
  .domain([0.4, 1.0])
  .interpolator(d3.interpolateRgbBasis([
    "#A50026","#F67E4B","#FEDA8B","#98CAE1","#4A7BB7","#364B9A"
  ]));

// ── Database ──────────────────────────────────────────────────────────────────

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

/** Returns the full country name for a given ISO3 code, with defunct years if applicable. */
export function getCountryName(code) {
  const r = query("SELECT country_name FROM countries WHERE ms_code = ?", [code]);
  const name = r.length ? r[0].country_name : code;
  const d = DEFUNCT[code];
  return d ? `${d.name} (${d.founded}–${d.end})` : name;
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

/**
 * Returns bloc badge HTML for a country code using Paul Tol's Muted palette.
 */
export function blocBadges(code) {
  const badges = Object.entries(BLOCS)
    .filter(([, codes]) => codes.includes(code))
    .map(([name]) => {
      const color = BLOC_COLORS[name] ?? "#888";
      // Lighten the bg by adding opacity
      return `<span style="font-size:8px;letter-spacing:0.06em;text-transform:uppercase;
        background:${color}22;color:${color};border:1px solid ${color}55;
        padding:1px 5px;border-radius:3px;
        font-family:'Outfit',sans-serif;flex-shrink:0;">${name}</span>`;
    });
  return badges.join(" ");
}

// ── DNA stripe ────────────────────────────────────────────────────────────────

/**
 * Renders the DNA stripe — one colored vertical stripe per year showing
 * average agreement score. Shared between country.html and story.html.
 * Requires a #dna-svg element and a #dna-tooltip element in the DOM.
 *
 * @param {string} msCode - ISO3 country code to render for
 */
export function renderDNA(msCode, svgId = "dna-svg") {
  const rows = query(
    "SELECT year, consensus FROM mat_consensus_overall WHERE ms_code = ? ORDER BY year",
    [msCode]
  );
  if (!rows.length) return;

  const svgNode = document.getElementById(svgId);
  if (!svgNode) return;
  svgNode.style.width = "100%";
  const w = Math.max(100, svgNode.parentElement?.clientWidth || svgNode.parentElement?.offsetWidth || 600);

  const svg = d3.select(`#${svgId}`);
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