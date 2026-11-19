// Identity attestation for delegated Microsoft Graph mail access.
// A successful OAuth token exchange alone does not identify the mailbox.
const GRAPH_ME="https://graph.microsoft.com/v1.0/me?$select=id,userPrincipalName,mail";
const ID=/^[A-Za-z0-9._@-]{1,256}$/;
export async function verifyMicrosoftMailbox(accessToken,{
  fetchImpl=fetch,expectedAccountId=null
}={}) {
  if(typeof accessToken!=="string" || !accessToken)
    throw new Error("missing_graph_access_token");
  const response=await fetchImpl(GRAPH_ME,{
    method:"GET",redirect:"error",
    headers:{Authorization:"Bearer "+accessToken,Accept:"application/json"}
  });
  if(!response.ok)throw new Error("graph_identity_http_"+response.status);
  const profile=await response.json();
  if(!profile || typeof profile.id!=="string" || !ID.test(profile.id))
    throw new Error("invalid_graph_identity");
  if(expectedAccountId!==null && profile.id!==expectedAccountId)
    throw new Error("graph_identity_mismatch");
  // Never infer identity from unverified email fields or return personal mail data.
  return {accountId:profile.id};
}
