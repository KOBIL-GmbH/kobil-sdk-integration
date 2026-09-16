'use strict';
const RELEASE = Object.freeze({version:'0.3.3', credentialSchema:1, tag:'v0.3.3', commit:'6736dc9f8cde8bbc29e4d484575677f86b30e36e', repository:'https://github.com/KOBIL-GmbH/kobil-sdk-integration.git'});
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function connectionInfo(data) {
  if (!data || typeof data !== 'object' || Array.isArray(data)) throw Error('Choose a JSON connection object.');
  const https = value => { try {const u = new URL(value);return u.protocol==='https:' && !u.username && !u.password && !u.search && !u.hash;} catch {return false;} };
  if (!data.environment || !data.tenant || !https(data.ast_url)) throw Error('Environment, tenant and an HTTPS AST URL are required.');
  if (!Array.isArray(data.services) || !data.services.length || data.services.some(s=>!s.name || !https(s.url))) throw Error('Provide the complete named HTTPS service map from your deployment.');
  if (new Set(data.services.map(s=>s.name)).size!==data.services.length) throw Error('Service names must be unique.');
  if(data.schema_version!==undefined){
    if(data.schema_version!==2 || data.oauth!==undefined || data.token_env!==undefined)throw Error('Invalid or mixed authentication schema.');
    const keys=(obj,allowed)=>{if(!obj||typeof obj!=='object'||Array.isArray(obj)||Object.keys(obj).some(k=>!allowed.includes(k))||allowed.some(k=>obj[k]===undefined))throw Error('Invalid credential configuration.');};
    const ref=(r,nested=false)=>{
      const fields={env:['provider','name'],keyring:['provider','service','account'],age:['provider','store','identity','service','account']}[r?.provider];
      if(!fields)throw Error('Unsupported credential provider.');
      const hasFallback=Object.hasOwn(r,'fallback');
      if(hasFallback&&(r.provider!=='keyring'||nested))throw Error('Invalid credential fallback.');
      keys(r,hasFallback?[...fields,'fallback']:fields);
      if(r.provider==='env'&&!/^KOBIL_[A-Z0-9_]+$/.test(r.name))throw Error('Use a KOBIL_ secret variable.');
      if(r.provider!=='env'&&['service','account'].some(k=>typeof r[k]!=='string'||!r[k]||r[k].length>256||/[\x00-\x1f]/.test(r[k])))throw Error('Exact service and account are required.');
      if(r.provider==='age'&&['store','identity'].some(k=>typeof r[k]!=='string'||!require('node:path').isAbsolute(r[k])))throw Error('Use absolute encrypted-store and identity paths.');
      if(hasFallback){ref(r.fallback,true);if(r.fallback.provider!=='age')throw Error('Only explicit age fallback is supported.');}
      return JSON.parse(JSON.stringify(r));
    };
    const a=data.auth;
    if(a?.type==='oauth_client_credentials'){keys(a,['type','token_url','client_id','credential']);if(!https(a.token_url)||typeof a.client_id!=='string'||!a.client_id)throw Error('Invalid OAuth configuration.');}
    else if(a?.type==='bearer')keys(a,['type','credential']);else throw Error('Unsupported authentication mode.');
    const credential=ref(a.credential);
    const clean={schema_version:2,environment:data.environment,tenant:data.tenant,ast_url:data.ast_url,services:data.services.map(s=>({name:s.name,url:s.url})),auth:{...a,credential}};
    return {config:clean,secretName:credential.provider==='env'?credential.name:null,provider:credential.provider};
  }
  if (!!data.oauth === !!data.token_env) throw Error('Configure exactly one of oauth or token_env.');
  let secretName;
  if(data.oauth){
    if(!https(data.oauth.token_url)||!data.oauth.client_id) throw Error('OAuth token URL and client ID are required.');
    secretName=data.oauth.client_secret_env;
  } else secretName=data.token_env;
  if(typeof secretName!=='string'||!/^KOBIL_[A-Z0-9_]+$/.test(secretName)) throw Error('Use a KOBIL_ prefixed environment variable for the secret, for example KOBIL_SDK_CLIENT_SECRET.');
  // Only allow documented, non-secret connection fields into persisted config.
  const clean={environment:data.environment,tenant:data.tenant,ast_url:data.ast_url,services:data.services.map(s=>({name:s.name,url:s.url}))};
  if(data.oauth)clean.oauth={token_url:data.oauth.token_url,client_id:data.oauth.client_id,client_secret_env:secretName};else clean.token_env=secretName;
  return {config:clean,secretName};
}
function skillText(root) { return `---\nname: kobil-sdk-release\ndescription: Build KOBIL Kotlin Android, Swift iOS and Flutter Android/iOS apps with the pinned SDK integration release.\n---\n\nRead and follow [the KOBIL SDK skill](<${root}/skills/kobil-sdk/SKILL.md>). Resolve references relative to that canonical file. Use the KOBIL SDK Release MCP. Keep credentials and supplied SDK binaries outside source control.\n`; }
function agentText(root) { return `---\nname: KOBIL Release Builder\ndescription: Build and test mobile apps using the version-pinned KOBIL SDK integration skill.\ntools: ['read', 'search', 'edit', 'execute', 'kobil-sdk-release/*']\nuser-invocable: true\n---\n\nRead and follow [the KOBIL SDK skill](<${root}/skills/kobil-sdk/SKILL.md>) before any integration work. Resolve its references from that canonical path. Use only that skill and its bundled references for the integration. Follow workspace instructions.\n\nCreate the requested fresh app or extend the user's chosen app, build it and verify it on the requested available device. Support Kotlin Android, Swift iOS and Flutter Android/iOS. Ask for missing platform, folder, app identifier and feature choices. Use KOBIL SDK Release tools for planning and backend setup. Confirm the target environment before writes. Never infer a deployment from examples. SDK binaries arrive separately. Record actual warning/runtime/fatal diagnostics, test outcomes and blockers. Never expose JWTs, PINs, activation codes or credentials. Missing capabilities such as test-user provisioning require the user's help, not guessed credentials. Maintain an INTEGRATION.md with build and runtime results separately.\n`; }
module.exports={RELEASE,escapeHtml,connectionInfo,skillText,agentText};
