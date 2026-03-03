function _getThemeCookie(){
  return document.cookie.split('; ').find((row)=>row.startsWith('theme='))?.split('=')[1]||null;
}

function _setThemeCookie(theme){
  document.cookie=`theme=${theme}; max-age=${365 * 24 * 3600}; path=/; samesite=strict`;
}

function _applyTheme(theme){
  document.documentElement.dataset.theme=theme;
  const btn=document.getElementById('theme-toggle');
  if(btn)btn.textContent=theme==='dark'?'Mode clair':'Mode sombre';
}

function toggleTheme(){
  const current=document.documentElement.dataset.theme||'light';
  const next=current==='dark'?'light':'dark';
  _applyTheme(next);
  _setThemeCookie(next);
}

(function _initTheme(){
  const saved=_getThemeCookie();
  if(saved==='dark'||saved==='light'){
    _applyTheme(saved);
  }else if(window.matchMedia?.('(prefers-color-scheme: dark)').matches){
    _applyTheme('dark');
  }else{
    _applyTheme('light');
  }
})();

