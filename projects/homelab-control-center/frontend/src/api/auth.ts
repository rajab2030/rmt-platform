// RMT-CAP-09 -- operator token handling. Client-side only; never logged,
// never sent to the evidence stores. Stored in the browser (localStorage).
const TOKEN_KEY = "rmt_operator_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (token === "") {
    clearToken();
    return;
  }
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function hasToken(): boolean {
  const t = getToken();
  return !!t && t.length > 0;
}
