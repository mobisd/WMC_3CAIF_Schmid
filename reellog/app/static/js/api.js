// Thin fetch wrappers that automatically attach the CSRF token.
//
// Flask-WTF's CSRFProtect requires the token on every mutating request. We read
// it from the <meta name="csrf-token"> tag rendered by base.html and send it as
// the X-CSRFToken header — the header name CSRFProtect checks by default.

function csrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute("content") : "";
}

async function request(method, url, body) {
  const opts = {
    method,
    headers: {
      "X-CSRFToken": csrfToken(),
      "X-Requested-With": "fetch",
    },
    // Same-origin cookies carry the session; never send the token in the body.
    credentials: "same-origin",
  };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }

  const resp = await fetch(url, opts);
  let data = null;
  try {
    data = await resp.json();
  } catch {
    data = null;
  }
  if (!resp.ok) {
    const message =
      (data && data.error) || `Request failed (${resp.status}).`;
    throw new Error(message);
  }
  return data;
}

export const api = {
  get: (url) => request("GET", url),
  post: (url, body) => request("POST", url, body ?? {}),
  patch: (url, body) => request("PATCH", url, body ?? {}),
  del: (url) => request("DELETE", url),
};
