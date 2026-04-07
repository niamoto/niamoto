/**
 * Transforme le HTML d'une preview de widget pour appliquer des overrides
 * côté iframe : dimensionnement plein écran et masquage des contrôles
 * Leaflet pour les miniatures non-interactives.
 *
 * Le script généré est injecté tout au début de `<head>` afin de poser un
 * `Object.defineProperty` sur `window.Plotly` AVANT que le bundle Plotly ne
 * s'auto-assigne. Au moment où la chart appelle `Plotly.newPlot/react/plot`,
 * notre wrapper a déjà modifié le layout, la chart est donc rendue
 * directement à la bonne taille sans réactiver le chemin interactif.
 */
export interface PreviewOverrideOptions {
  /**
   * Étire le chart pour remplir l'iframe (utile dans le panneau de détail).
   * Supprime `width`/`height` fixes posés en mode preview par
   * `plotly_utils.py`, garde le rendu statique, puis déclenche un resize
   * post-rendu pour stabiliser le layout.
   */
  fullSize?: boolean
  /**
   * Masque les contrôles Leaflet via CSS (utile pour les miniatures où
   * l'utilisateur ne peut pas interagir avec la carte).
   */
  hideLeafletControls?: boolean
}

function buildScript(opts: PreviewOverrideOptions): string {
  if (!opts.fullSize) return ''

  return `<script>(function(){
var current;
function wrap(p){
  if(!p||p.__niamotoOverridden)return p;
  p.__niamotoOverridden=true;
  ['newPlot','react','plot'].forEach(function(m){
    var orig=p[m];
    if(typeof orig!=='function')return;
    p[m]=function(){
      var args=Array.prototype.slice.call(arguments);
      var layout=Object.assign({},args[2]||{});
      layout.autosize=true;
      delete layout.width;
      delete layout.height;
      args[2]=layout;
      var result=orig.apply(this,args);
      if(result&&typeof result.then==='function'){
        return result.then(function(gd){
          if(gd&&p.Plots&&typeof p.Plots.resize==='function'){
            requestAnimationFrame(function(){p.Plots.resize(gd);});
          }
          return gd;
        });
      }
      return result;
    };
  });
  return p;
}
if(window.Plotly){wrap(window.Plotly);return;}
try{
  Object.defineProperty(window,'Plotly',{
    configurable:true,
    get:function(){return current;},
    set:function(v){current=wrap(v);}
  });
}catch(e){}
})();</script>`
}

function buildStyle(opts: PreviewOverrideOptions): string {
  if (!opts.hideLeafletControls) return ''
  return `<style>.leaflet-control{display:none!important}</style>`
}

/**
 * Injecte les overrides de preview au tout début de `<head>`.
 *
 * Ordre d'injection important :
 * 1. Le script Plotly-wrapping doit s'exécuter AVANT le `<script src="...plotly...">`
 *    déjà placé par `wrap_html_response` côté Python (sinon Plotly est déjà chargé
 *    et le `defineProperty` n'intercepte rien de neuf).
 * 2. Les styles Leaflet sont également placés dans `<head>` pour éviter tout flash.
 */
export function injectPreviewOverrides(
  html: string,
  opts: PreviewOverrideOptions = {},
): string {
  if (!html) return html
  const script = buildScript(opts)
  const style = buildStyle(opts)
  const payload = script + style
  if (!payload) return html

  const headMatch = html.match(/<head[^>]*>/i)
  if (headMatch && headMatch.index !== undefined) {
    const insertAt = headMatch.index + headMatch[0].length
    return html.slice(0, insertAt) + payload + html.slice(insertAt)
  }
  // Fallback défensif : si pas de <head>, préfixer le document.
  return payload + html
}
