// Google Maps basemap via the official Maps JavaScript API (rendered under Leaflet by GoogleMutant).
// The key comes from VITE_GOOGLE_MAPS_KEY in dashboard-app/.env.local (git-ignored).
// If the key is missing, the script fails, or Google rejects the key, callers fall back to Esri tiles.
const KEY = import.meta.env.VITE_GOOGLE_MAPS_KEY;
let loading = null;
let failed = false;
const failListeners = new Set();

export const googleFailed = () => failed;
export const onGoogleFail = fn => { failListeners.add(fn); return () => failListeners.delete(fn); };
const fail = () => { if (failed) return; failed = true; failListeners.forEach(f => f()); };
// used when the script loads but Google draws no map (e.g. the key's daily quota is used up)
export const giveUpGoogle = msg => { if (!failed) console.warn(msg); fail(); };

export function loadGoogleMaps() {
  if (!KEY || failed) return Promise.resolve(false);
  if (loading) return loading;
  loading = new Promise(resolve => {
    let done = false;
    const finish = ok => { if (!done) { done = true; if (!ok) fail(); resolve(ok); } };
    window.gm_authFailure = () => { console.warn('Google Maps menolak kunci API; memakai peta cadangan.'); finish(false); fail(); };
    window.__da2026GoogleReady = async () => {
      try { await window.google.maps.importLibrary('maps'); finish(true); } catch { finish(false); }
    };
    const s = document.createElement('script');
    s.src = `https://maps.googleapis.com/maps/api/js?key=${KEY}&loading=async&callback=__da2026GoogleReady&v=weekly&language=id&region=ID`;
    s.async = true;
    s.onerror = () => finish(false);
    document.head.appendChild(s);
    // no timeout-based failure: a slow connection only delays the switch to Google (fallback shows meanwhile)
  });
  return loading;
}
