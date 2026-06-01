const BASE = "/api";

async function req(method, path, body) {
  const opts = {
    method,

    headers: {
      "Content-Type": "application/json",
    },

    ...(body !== undefined && {
      body: JSON.stringify(body),
    }),
  };

  const res = await fetch(
    `${BASE}${path}`,
    opts
  );

  if (!res.ok) {
    throw new Error(
      `${res.status} ${res.statusText}`
    );
  }

  return res.json();
}

export const getValue = (key) =>
  req(
    "GET",
    `/cache/${encodeURIComponent(key)}`
  );

export const setValue = (
  key,
  value,
  ttl = 60,
  wt = false
) =>
  req(
    "POST",
    `/cache/${encodeURIComponent(key)}`,
    {
      value,
      ttl_seconds: ttl,
      write_through: wt,
    }
  );

export const deleteValue = (key) =>
  req(
    "DELETE",
    `/cache/${encodeURIComponent(key)}`
  );

export const setPolicy = (
  policy,
  capacity = 128
) =>
  req("POST", "/policy", {
    policy,
    capacity,
  });

export const getStats = () =>
  req("GET", "/stats");

export const getHealth = () =>
  req("GET", "/health");

export function subscribeToEvents(
  onEvent,
  onError
) {
  const es = new EventSource(
    `${BASE}/events`
  );

  es.onopen = () => {
    console.log("[SSE] connected");
  };

  es.onmessage = (e) => {
    try {
      const parsed = JSON.parse(e.data);

      console.log(
        "[SSE EVENT]",
        parsed
      );

      onEvent(parsed);
    }

    catch (err) {
      console.error(
        "[SSE parse error]",
        err
      );
    }
  };

  es.onerror = (e) => {
    console.error("[SSE error]", e);

    onError?.(e);
  };

  return () => {
    console.log("[SSE] disconnected");

    es.close();
  };
}