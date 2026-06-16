import { createReadStream, existsSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, resolve } from "node:path";

const PORT = Number.parseInt(process.env.DATABRICKS_APP_PORT ?? "8000", 10);
const DIST_DIR = resolve("dist");
const WAREHOUSE_ID = process.env.DATABRICKS_WAREHOUSE_ID;
const DATABRICKS_HOST = normalizeDatabricksHost(process.env.DATABRICKS_HOST);

const MIME_TYPES = new Map([
  [".css", "text/css"],
  [".html", "text/html"],
  [".js", "text/javascript"],
  [".json", "application/json"],
  [".svg", "image/svg+xml"],
]);

function normalizeDatabricksHost(rawHost) {
  if (!rawHost) {
    return undefined;
  }

  const hostWithProtocol = rawHost.startsWith("http://") || rawHost.startsWith("https://") ? rawHost : `https://${rawHost}`;
  const parsedHost = new URL(hostWithProtocol);

  if (parsedHost.protocol !== "https:") {
    throw new Error("DATABRICKS_HOST must use https");
  }

  return parsedHost.origin;
}

function sendJson(response, statusCode, payload) {
  response.writeHead(statusCode, { "content-type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(payload));
}

async function getAccessToken() {
  const clientId = process.env.DATABRICKS_CLIENT_ID;
  const clientSecret = process.env.DATABRICKS_CLIENT_SECRET;

  if (!DATABRICKS_HOST || !clientId || !clientSecret) {
    throw new Error("Missing Databricks app OAuth environment variables");
  }

  const tokenResponse = await fetch(`${DATABRICKS_HOST}/oidc/v1/token`, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "client_credentials",
      scope: "all-apis",
      client_id: clientId,
      client_secret: clientSecret,
    }),
  });

  if (!tokenResponse.ok) {
    throw new Error(`Databricks token request failed: HTTP ${tokenResponse.status}`);
  }

  const tokenPayload = await tokenResponse.json();
  if (typeof tokenPayload.access_token !== "string") {
    throw new Error("Databricks token response did not include access_token");
  }
  return tokenPayload.access_token;
}

async function executeStatement(statement) {
  if (!DATABRICKS_HOST || !WAREHOUSE_ID) {
    throw new Error("Missing DATABRICKS_HOST or DATABRICKS_WAREHOUSE_ID");
  }

  const accessToken = await getAccessToken();
  const statementResponse = await fetch(`${DATABRICKS_HOST}/api/2.0/sql/statements`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${accessToken}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      warehouse_id: WAREHOUSE_ID,
      statement,
      wait_timeout: "50s",
      on_wait_timeout: "CONTINUE",
    }),
  });

  if (!statementResponse.ok) {
    throw new Error(`Databricks statement request failed: HTTP ${statementResponse.status}`);
  }

  const statementPayload = await statementResponse.json();
  if (statementPayload.status?.state !== "SUCCEEDED") {
    throw new Error(statementPayload.status?.error?.message ?? "Databricks statement did not succeed");
  }
  return {
    columns: statementPayload.manifest?.schema?.columns ?? [],
    rows: statementPayload.result?.data_array ?? [],
  };
}

async function buildReadinessSummary() {
  const [hmisSummary, facilityVerdicts] = await Promise.all([
    executeStatement(`
      SELECT
        state_name,
        anc_four_plus_rate_percent,
        institutional_delivery_to_live_birth_ratio_percent,
        fully_immunized_to_live_birth_ratio_percent,
        data_caution
      FROM data_readiness_desk.pipeline.gold_hmis_state_indicator_summary
      ORDER BY state_name
      LIMIT 8
    `),
    executeStatement(`
      SELECT
        source_state_name,
        total_facilities,
        valid_coordinate_facilities,
        numeric_score,
        band,
        binding_reason,
        data_caution
      FROM data_readiness_desk.pipeline.gold_facility_verdicts
      ORDER BY numeric_score ASC
      LIMIT 8
    `),
  ]);

  return {
    status: "ok",
    hmisSummary,
    facilityVerdicts,
  };
}

function sendStatic(response, requestUrl) {
  const parsedUrl = new URL(requestUrl ?? "/", `http://localhost:${PORT}`);
  const pathname = parsedUrl.pathname === "/" ? "/index.html" : parsedUrl.pathname;
  const filePath = resolve(join(DIST_DIR, pathname));

  if (!filePath.startsWith(DIST_DIR) || !existsSync(filePath)) {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("Not found");
    return;
  }

  response.writeHead(200, {
    "content-type": MIME_TYPES.get(extname(filePath)) ?? "application/octet-stream",
  });
  createReadStream(filePath).pipe(response);
}

const server = createServer((request, response) => {
  if (request.url === "/api/readiness-summary") {
    buildReadinessSummary()
      .then((payload) => sendJson(response, 200, payload))
      .catch((error) => {
        console.error(error);
        sendJson(response, 503, {
          status: "unavailable",
          message: error instanceof Error ? error.message : "Unknown app query error",
        });
      });
    return;
  }

  sendStatic(response, request.url);
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`Data Readiness Desk app listening on ${PORT}`);
});

process.on("SIGTERM", () => {
  server.close(() => process.exit(0));
});
