// ======================== Shared API fetch with bearer token ========================
// Single source of truth for authenticated /api/* requests:
//   1. reads the admin token from localStorage("autologminer_token")
//   2. injects "Authorization: Bearer <token>" when present
//   3. on 401 shows a token dialog, stores the entry, then retries the request once
// Loaded via <script src="/static/js/api.js"></script> before app.js; defines window.apiFetch.

(function () {
  const TOKEN_KEY = "autologminer_token";

  let pendingPrompt = null;

  function readToken() {
    try { return localStorage.getItem(TOKEN_KEY) || ""; } catch (e) { return ""; }
  }

  function withToken(options, token) {
    const opts = Object.assign({}, options);
    const headers = Object.assign({}, opts.headers || {});
    if (token) headers["Authorization"] = "Bearer " + token;
    opts.headers = headers;
    return opts;
  }

  function showTokenDialog() {
    return new Promise(function (resolve) {
      const overlay = document.createElement("div");
      overlay.id = "api-token-modal";
      overlay.className = "modal-overlay";
      overlay.innerHTML =
        '<div class="modal">' +
          '<h3>需要管理员令牌</h3>' +
          '<p class="modal-desc">接口返回 401，请输入 ADMIN_TOKEN 后重试。</p>' +
          '<input id="api-token-input" type="password" placeholder="ADMIN_TOKEN" autocomplete="off">' +
          '<div class="modal-actions">' +
            '<button type="button" id="api-token-cancel" class="btn btn-outline btn-sm">取消</button>' +
            '<button type="button" id="api-token-save" class="btn btn-primary btn-sm">保存并重试</button>' +
          '</div>' +
        '</div>';
      document.body.appendChild(overlay);

      const input = document.getElementById("api-token-input");
      function finish(value) {
        overlay.remove();
        resolve(value);
      }
      document.getElementById("api-token-save").addEventListener("click", function () { finish(input.value.trim()); });
      document.getElementById("api-token-cancel").addEventListener("click", function () { finish(""); });
      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter") finish(input.value.trim());
        if (e.key === "Escape") finish("");
      });
      input.focus();
    });
  }

  // Concurrent 401s share one dialog instead of stacking modals.
  function requestToken() {
    if (!pendingPrompt) {
      pendingPrompt = showTokenDialog().then(function (token) {
        pendingPrompt = null;
        return token;
      });
    }
    return pendingPrompt;
  }

  async function apiFetch(url, options) {
    let resp = await fetch(url, withToken(options, readToken()));
    if (resp.status !== 401) return resp;

    const token = await requestToken();
    if (!token) return resp;
    localStorage.setItem(TOKEN_KEY, token);
    return fetch(url, withToken(options, token));
  }

  window.apiFetch = apiFetch;
})();
