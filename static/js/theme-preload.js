/* Early theme application to prevent initial flicker.
 * Runs before CSS fully parses and before ThemeManager loads.
 * Chooses theme from session/local storage; defaults to 'light'.
 */
(function() {
  try {
    var t = sessionStorage.getItem('selectedTheme') || localStorage.getItem('selectedTheme') || 'light';
    // attach classes ASAP
    document.documentElement.classList.add('js', 'theme-' + t);
    var addBody = function(){
      document.body.classList.add('theme-' + t, 'theme-preload');
    };
    if (document.body) addBody(); else document.addEventListener('DOMContentLoaded', addBody);
  } catch (e) { /* no-op */ }
})();
