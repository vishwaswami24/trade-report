import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const sectorPattern = /^[A-Za-z][A-Za-z\s&-]{1,39}$/;

function normalizeSector(sector) {
  const normalized = sector.replace(/-/g, " ").replace(/\s+/g, " ").trim();
  const compact = normalized.replace(/\s/g, "").replace(/&/g, "");

  if (!normalized || normalized.length < 2 || !compact || !/^[A-Za-z]+$/.test(compact)) {
    return null;
  }

  return normalized.toLowerCase();
}

export async function POST(request) {
  const backendBaseUrl = process.env.BACKEND_BASE_URL;
  const backendApiKey = process.env.BACKEND_API_KEY;

  if (!backendBaseUrl || !backendApiKey) {
    return NextResponse.json(
      {
        detail:
          "Frontend is missing BACKEND_BASE_URL or BACKEND_API_KEY. Add them in frontend/.env.local.",
      },
      { status: 500 },
    );
  }

  let body;

  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  const sector = typeof body?.sector === "string" ? body.sector.trim() : "";

  if (!sector || !sectorPattern.test(sector)) {
    return NextResponse.json(
      {
        detail: "Sector must contain 2-40 characters using letters, spaces, ampersands, or hyphens.",
      },
      { status: 422 },
    );
  }

  const normalizedSector = normalizeSector(sector);

  if (!normalizedSector) {
    return NextResponse.json(
      { detail: "Sector must contain only letters, spaces, or ampersands." },
      { status: 422 },
    );
  }

  let upstreamResponse;

  try {
    upstreamResponse = await fetch(
      `${backendBaseUrl.replace(/\/$/, "")}/analyze/${encodeURIComponent(normalizedSector)}`,
      {
        method: "GET",
        headers: {
          Accept: "text/markdown, application/json",
          "X-API-Key": backendApiKey,
          ...(request.headers.get("cookie")
            ? { cookie: request.headers.get("cookie") }
            : {}),
        },
        cache: "no-store",
      },
    );
  } catch {
    return NextResponse.json(
      { detail: "Could not reach the FastAPI backend. Confirm it is running." },
      { status: 502 },
    );
  }

  const responseType = upstreamResponse.headers.get("content-type") || "";
  const setCookie = upstreamResponse.headers.get("set-cookie");

  if (!upstreamResponse.ok) {
    let errorBody = { detail: "Backend request failed." };

    if (responseType.includes("application/json")) {
      try {
        errorBody = await upstreamResponse.json();
      } catch {
        errorBody = { detail: "Backend request failed." };
      }
    } else {
      const text = await upstreamResponse.text();
      if (text) {
        errorBody = { detail: text };
      }
    }

    const errorResponse = NextResponse.json(errorBody, {
      status: upstreamResponse.status,
    });

    if (setCookie) {
      errorResponse.headers.set("set-cookie", setCookie);
    }

    errorResponse.headers.set("Cache-Control", "no-store");
    return errorResponse;
  }

  const report = await upstreamResponse.text();
  const successResponse = NextResponse.json(
    {
      report,
      meta: {
        sessionId: upstreamResponse.headers.get("x-session-id"),
        rateLimit: {
          limit: upstreamResponse.headers.get("x-ratelimit-limit"),
          remaining: upstreamResponse.headers.get("x-ratelimit-remaining"),
          reset: upstreamResponse.headers.get("x-ratelimit-reset"),
        },
      },
    },
    { status: 200 },
  );

  if (setCookie) {
    successResponse.headers.set("set-cookie", setCookie);
  }

  successResponse.headers.set("Cache-Control", "no-store");
  return successResponse;
}
