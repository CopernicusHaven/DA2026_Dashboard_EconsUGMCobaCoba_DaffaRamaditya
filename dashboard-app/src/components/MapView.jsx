import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Polyline, Tooltip, useMap } from 'react-leaflet';
import GoogleMutant from 'leaflet.gridlayer.googlemutant/src/Leaflet.GoogleMutant.mjs';
import { giveUpGoogle, googleFailed, loadGoogleMaps, onGoogleFail } from '../lib/googleMaps.js';

// Basemap = visual background only (not analysis data).
// Google Maps roadmap when a key is configured (official Maps JavaScript API, Google logo + attribution
// drawn by Google); otherwise, or if Google refuses the key, the colourful Esri World Street Map.
function EsriTiles() {
  const [osm, setOsm] = useState(false);
  const [errors, setErrors] = useState(0);
  useEffect(() => { if (errors >= 4) setOsm(true); }, [errors]);
  return osm
    ? <TileLayer url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="© OpenStreetMap contributors" maxZoom={12} />
    : <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
      attribution="Peta dasar © Esri, HERE, Garmin, © OpenStreetMap contributors" maxZoom={12} eventHandlers={{ tileerror: () => setErrors(e => e + 1) }} />;
}

function GoogleTiles() {
  const map = useMap();
  useEffect(() => {
    const layer = new GoogleMutant({ type: 'roadmap', maxZoom: 12 });
    layer.addTo(map);
    // A key over its daily quota still loads the script but Google draws no tiles.
    // If no Google tile has arrived a few seconds after the map is on screen, use the Esri map instead.
    let t = 0;
    const check = () => {
      if (document.visibilityState !== 'visible') { t = setTimeout(check, 2000); return; }
      const c = layer.getContainer && layer.getContainer();
      if (!c || !c.querySelector('img')) giveUpGoogle('Google Maps tidak memuat peta; memakai peta cadangan Esri.');
    };
    t = setTimeout(check, 6000);
    return () => { clearTimeout(t); map.removeLayer(layer); };
  }, [map]);
  return null;
}

function BaseTiles() {
  // Google when ready; the Esri map is shown if Google is slow (after 1.2 s) or refuses the key
  const ready = () => !!(window.google && window.google.maps && window.google.maps.Map);
  const [mode, setMode] = useState(() => (googleFailed() ? 'esri' : ready() ? 'google' : 'wait'));
  useEffect(() => {
    let live = true;
    const t = setTimeout(() => { if (live) setMode(m => (m === 'wait' ? 'esri' : m)); }, 1200);
    loadGoogleMaps().then(ok => { if (live) setMode(ok ? 'google' : 'esri'); });
    const off = onGoogleFail(() => { if (live) setMode('esri'); });
    return () => { live = false; clearTimeout(t); off(); };
  }, []);
  return mode === 'google' ? <GoogleTiles /> : mode === 'esri' ? <EsriTiles /> : null;
}

// smoothly re-frame the map when the set of visible stations changes
const padFor = map => (map.getContainer().clientWidth < 520 ? [14, 14] : [36, 36]);
const TOUCH = typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(pointer: coarse)').matches;

function FitTo({ points }) {
  const map = useMap();
  const key = points.map(p => p.join(',')).join('|');
  useEffect(() => {
    if (!points.length) return;
    if (points.length === 1) map.flyTo(points[0], 7, { duration: 0.9 });
    else map.flyToBounds(points, { padding: padFor(map), duration: 0.9, maxZoom: 7 });
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  // the container can still be resizing when Leaflet first measures it (cards animate in):
  // re-measure and re-frame whenever its size actually changes
  useEffect(() => {
    const el = map.getContainer();
    let w = el.clientWidth, h = el.clientHeight;
    const ro = new ResizeObserver(() => {
      if (el.clientWidth === w && el.clientHeight === h) return;
      w = el.clientWidth; h = el.clientHeight;
      map.invalidateSize();
      if (points.length > 1) map.fitBounds(points, { padding: padFor(map), maxZoom: 7, animate: false });
      else if (points.length === 1) map.setView(points[0], 7, { animate: false });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

export default function MapView({ markers, lines = [], height = 460, fitPoints }) {
  const pts = fitPoints || markers.map(m => m.pos);
  return (
    <div className="map" style={{ height }}>
      <MapContainer bounds={pts.length > 1 ? pts : [[-9, 95], [6, 141]]} boundsOptions={{ padding: [24, 24] }} scrollWheelZoom={false} dragging={!TOUCH} zoomSnap={0.25} style={{ height: '100%', width: '100%' }}>
        <BaseTiles />
        <FitTo points={pts} />
        {lines.map((l, i) => (
          <Polyline key={'l' + i} positions={l.pos} pathOptions={l.style}>
            {l.tip && <Tooltip sticky>{l.tip}</Tooltip>}
          </Polyline>
        ))}
        {markers.map(m => (
          <CircleMarker key={m.id} center={m.pos} radius={m.radius} pathOptions={m.style}
            eventHandlers={{ click: () => m.onClick && m.onClick(), mouseover: e => e.target.setStyle({ weight: 3 }), mouseout: e => e.target.setStyle({ weight: m.style.weight || 1 }) }}>
            <Tooltip direction="top" offset={[0, -4]}>{m.tip}</Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
}
