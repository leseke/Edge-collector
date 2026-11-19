// Delegated Microsoft OAuth token refresh for a confidential server-side client.
// The app registration, initial user consent, encrypted token store and scheduler
// are intentionally injected; no production auth setup or persistent secrets here.
const TENANTS = /^(?:common|consumers|organizations|[0-9a-f]{8}-[0-9a-f-]{27,})$/i;
export async function refreshMicrosoftGraphToken({
  tenant="consumers",clientId,clientSecret,refreshToken,fetchImpl=fetch
}) {
  if (!TENANTS.test(tenant)) throw new Error("invalid_microsoft_tenant");
  if (typeof clientId !== "string" || !/^[0-9a-f-]{36}$/i.test(clientId))
    throw new Error("invalid_microsoft_client_id");
  if (!clientSecret || !refreshToken) throw new Error("missing_oauth_secret");
  const url="https://login.microsoftonline.com/"+tenant+"/oauth2/v2.0/token";
  const data=new URLSearchParams({
    client_id:clientId,client_secret:clientSecret,grant_type:"refresh_token",
    refresh_token:refreshToken,scope:"offline_access Mail.Read User.Read"
  });
  const response=await fetchImpl(url,{method:"POST",redirect:"error",
    headers:{"Content-Type":"application/x-www-form-urlencoded"},body:data.toString()});
  if (!response.ok) {
    // No response body: identity provider may echo sensitive token details.
    throw new Error("microsoft_token_http_"+response.status);
  }
  const raw=await response.json();
  if (typeof raw.access_token!=="string" || !raw.access_token ||
      !Number.isFinite(raw.expires_in) || raw.expires_in<=0)
    throw new Error("microsoft_token_invalid_response");
  return {accessToken:raw.access_token,
    replacementRefreshToken:typeof raw.refresh_token==="string" && raw.refresh_token
      ? raw.refresh_token : refreshToken,
    expiresInSeconds:raw.expires_in};
}

export async function runWithMicrosoftToken({
  credentialStore,clientId,clientSecret,tenant="consumers",fetchImpl=fetch,run
}) {
  if (!credentialStore?.load || !credentialStore?.save || typeof run!=="function")
    throw new Error("missing_secure_credential_store");
  const current=await credentialStore.load();
  if (!current?.refreshToken) throw new Error("missing_refresh_token");
  const token=await refreshMicrosoftGraphToken({tenant,clientId,clientSecret,
    refreshToken:current.refreshToken,fetchImpl});
  // Persist replacement before using short-lived access token; if it fails,
  // fail closed and never risk discarding refreshed credentials.
  if (token.replacementRefreshToken!==current.refreshToken)
    await credentialStore.save({refreshToken:token.replacementRefreshToken});
  return run(token.accessToken);
}
