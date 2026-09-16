const {test}=require('node:test');const assert=require('node:assert/strict');
const {connectionInfo,escapeHtml,agentText,RELEASE}=require('../src/core');
const config=()=>({environment:'dev',tenant:'example',ast_url:'https://ast.example',services:[{name:'astLogin',url:'https://ast.example'}],oauth:{token_url:'https://idp.example/token',client_id:'sdk',client_secret_env:'KOBIL_SDK_CLIENT_SECRET'}});
test('sanitizes imported connection and never persists inline secrets',()=>{let c=config();c.password='private';c.oauth.client_secret='private';const r=connectionInfo(c);assert(!JSON.stringify(r).includes('private'));assert.equal(r.secretName,'KOBIL_SDK_CLIENT_SECRET');});
test('rejects dangerous or ambiguous runtime configuration',()=>{for(const change of [c=>c.ast_url='http://ast.example',c=>c.oauth.client_secret_env='PATH',c=>c.token_env='KOBIL_TOKEN',c=>c.services.push(c.services[0]),c=>c.oauth.token_url='https://user:password@idp.example/token']){const c=config();change(c);assert.throws(()=>connectionInfo(c));}});
test('escapes injected webview markup',()=>assert.equal(escapeHtml('<img onerror="x">'), '&lt;img onerror=&quot;x&quot;&gt;'));
test('release agent explicitly enables file and terminal tools',()=>{const s=agentText('/release');assert(s.includes("'edit', 'execute'"));assert(s.includes("'kobil-sdk-release/*'"));assert(s.includes('/release/skills/kobil-sdk/SKILL.md'));assert.match(RELEASE.commit,/^[a-f0-9]{40}$/);});
test('v2 keyring and age refs are preserved without requiring a SecretStorage value',()=>{
 const c=config();delete c.oauth;c.schema_version=2;c.auth={type:'bearer',credential:{provider:'keyring',service:'test',account:'exact'}};
 const r=connectionInfo(c);assert.equal(r.provider,'keyring');assert.equal(r.secretName,null);assert.deepEqual(r.config.auth,c.auth);
 c.auth.credential.password='canary';assert.throws(()=>connectionInfo(c));delete c.auth.credential.password;
 c.token_env='KOBIL_TOKEN';assert.throws(()=>connectionInfo(c));
});
test('v2 rejects unsafe secret vars, unknown auth fields and fallback providers',()=>{
 const c=config();delete c.oauth;c.schema_version=2;c.auth={type:'bearer',credential:{provider:'env',name:'PATH'}};assert.throws(()=>connectionInfo(c));
 c.auth.credential={provider:'keyring',service:'s',account:'a',fallback:{provider:'env',name:'KOBIL_TOKEN'}};assert.throws(()=>connectionInfo(c));
});
