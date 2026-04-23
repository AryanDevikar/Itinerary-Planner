import { useState, useEffect } from 'react'
import axios from 'axios'
import { GoogleMap, LoadScript, Marker, InfoWindow, Polyline } from '@react-google-maps/api'
import './index.css'

const API      = import.meta.env.VITE_API_BASE_URL
const MAPS_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY

const mapStyles  = { width: '100%', height: '100%' }
const mapOptions = {
  disableDefaultUI: true, zoomControl: true,
  styles: [
    { featureType: 'poi', elementType: 'labels', stylers: [{ visibility: 'off' }] },
    { featureType: 'transit', stylers: [{ visibility: 'off' }] },
    { elementType: 'geometry', stylers: [{ color: '#f5f5f0' }] },
    { featureType: 'road', elementType: 'geometry', stylers: [{ color: '#ffffff' }] },
    { featureType: 'water', elementType: 'geometry', stylers: [{ color: '#dde8e0' }] },
  ]
}

const MODES = [
  { value: 'walking',   label: '🚶 Walk'    },
  { value: 'driving',   label: '🚗 Drive'   },
  { value: 'transit',   label: '🚌 Transit' },
  { value: 'bicycling', label: '🚲 Bike'    },
]

const PRICE = { PRICE_LEVEL_FREE: 'Free', PRICE_LEVEL_INEXPENSIVE: '$', PRICE_LEVEL_MODERATE: '$$', PRICE_LEVEL_EXPENSIVE: '$$$', PRICE_LEVEL_VERY_EXPENSIVE: '$$$$' }

// ── Input Screen ─────────────────────────────────────────────────
function InputScreen({ onSubmit, loading }) {
  const [message,  setMessage]  = useState('')
  const [maxStops, setMaxStops] = useState(4)
  const [mode,     setMode]     = useState('walking')

  return (
    <div style={{ minHeight:'100vh', display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', padding:'2rem' }}>
      <div style={{ maxWidth:560, width:'100%' }}>
        <p style={{ fontSize:13, letterSpacing:'0.12em', textTransform:'uppercase', color:'var(--accent)', marginBottom:'0.75rem', fontWeight:500 }}>Local Event Planner</p>
        <h1 style={{ fontSize:'clamp(2rem,5vw,3rem)', lineHeight:1.15, marginBottom:'0.5rem' }}>Where do you want<br/>to go today?</h1>
        <p style={{ color:'var(--text-secondary)', marginBottom:'2.5rem', fontSize:15 }}>Describe your interests, location, and when — we'll build your itinerary.</p>
        <form onSubmit={e => { e.preventDefault(); if (message.trim()) onSubmit(message, maxStops, mode) }}>
          <textarea value={message} onChange={e => setMessage(e.target.value)}
            placeholder="e.g. I want to visit coffee shops and bookstores in New Brunswick this Saturday afternoon"
            rows={4} style={{ width:'100%', padding:'1rem', border:'1.5px solid var(--border)', borderRadius:'var(--radius)', fontFamily:'DM Sans,sans-serif', fontSize:15, background:'var(--surface)', color:'var(--text-primary)', resize:'vertical', outline:'none', lineHeight:1.6 }}
            onFocus={e => e.target.style.borderColor='var(--accent)'}
            onBlur={e  => e.target.style.borderColor='var(--border)'} />
          <div style={{ display:'flex', alignItems:'center', gap:'1rem', margin:'1rem 0 1.5rem', flexWrap:'wrap' }}>
            <label style={{ fontSize:13, color:'var(--text-secondary)', display:'flex', alignItems:'center', gap:8 }}>
              Max stops
              <select value={maxStops} onChange={e => setMaxStops(Number(e.target.value))}
                style={{ border:'1px solid var(--border)', borderRadius:8, padding:'4px 8px', fontFamily:'DM Sans,sans-serif', fontSize:13, background:'var(--surface)', color:'var(--text-primary)' }}>
                {[2,3,4,5,6].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
            <div style={{ display:'flex', gap:6 }}>
              {MODES.map(m => (
                <button key={m.value} type="button" onClick={() => setMode(m.value)} style={{ padding:'4px 10px', borderRadius:20, fontSize:12, border:`1.5px solid ${mode===m.value?'var(--accent)':'var(--border)'}`, background:mode===m.value?'var(--accent-light)':'var(--surface)', color:mode===m.value?'var(--accent)':'var(--text-secondary)', cursor:'pointer', fontFamily:'DM Sans,sans-serif' }}>
                  {m.label}
                </button>
              ))}
            </div>
          </div>
          <button type="submit" disabled={loading || !message.trim()} style={{ width:'100%', padding:'0.875rem', background:loading?'var(--border)':'var(--accent)', color:loading?'var(--text-secondary)':'#fff', border:'none', borderRadius:'var(--radius)', fontFamily:'DM Sans,sans-serif', fontSize:15, fontWeight:500, cursor:loading?'not-allowed':'pointer' }}>
            {loading ? 'Planning your day...' : 'Plan my itinerary →'}
          </button>
        </form>
        <p style={{ marginTop:'1.5rem', fontSize:13, color:'var(--text-secondary)', textAlign:'center' }}>
          <a href={`${API}/auth/login`} style={{ color:'var(--accent)', textDecoration:'none' }}>Connect Google Calendar</a> to export your itinerary
        </p>
      </div>
    </div>
  )
}

// ── Place Detail Panel (Google Maps style) ───────────────────────
function PlaceDetailPanel({ stop, alternatives, onSwap, onRemove, onClose }) {
  const [details,    setDetails]    = useState(null)
  const [photoIndex, setPhotoIndex] = useState(0)
  const [loading,    setLoading]    = useState(true)

  useEffect(() => {
    setLoading(true)
    axios.get(`${API}/api/place/${stop.place_id}`)
      .then(r => setDetails(r.data))
      .catch(() => setDetails(null))
      .finally(() => setLoading(false))
  }, [stop.place_id])

  return (
    <div style={{ position:'fixed', top:0, right:0, width:420, height:'100vh', background:'var(--surface)', borderLeft:'1px solid var(--border)', zIndex:100, display:'flex', flexDirection:'column', overflowY:'auto', boxShadow:'-4px 0 24px rgba(0,0,0,0.08)' }}>

      {/* Photo carousel */}
      <div style={{ position:'relative', height:220, background:'var(--bg)', flexShrink:0 }}>
        {loading ? (
          <div style={{ height:'100%', display:'flex', alignItems:'center', justifyContent:'center', color:'var(--text-secondary)', fontSize:13 }}>Loading...</div>
        ) : details?.photos?.length > 0 ? (
          <>
            <img src={details.photos[photoIndex]} alt={stop.name}
              style={{ width:'100%', height:'100%', objectFit:'cover' }} />
            {details.photos.length > 1 && (
              <div style={{ position:'absolute', bottom:10, left:'50%', transform:'translateX(-50%)', display:'flex', gap:5 }}>
                {details.photos.map((_, i) => (
                  <div key={i} onClick={() => setPhotoIndex(i)} style={{ width:6, height:6, borderRadius:'50%', background:i===photoIndex?'#fff':'rgba(255,255,255,0.5)', cursor:'pointer' }} />
                ))}
              </div>
            )}
            {details.photos.length > 1 && (
              <>
                <button onClick={() => setPhotoIndex(i => Math.max(0, i-1))} style={{ position:'absolute', left:8, top:'50%', transform:'translateY(-50%)', background:'rgba(255,255,255,0.85)', border:'none', borderRadius:'50%', width:30, height:30, cursor:'pointer', fontSize:16 }}>‹</button>
                <button onClick={() => setPhotoIndex(i => Math.min(details.photos.length-1, i+1))} style={{ position:'absolute', right:8, top:'50%', transform:'translateY(-50%)', background:'rgba(255,255,255,0.85)', border:'none', borderRadius:'50%', width:30, height:30, cursor:'pointer', fontSize:16 }}>›</button>
              </>
            )}
          </>
        ) : (
          <div style={{ height:'100%', display:'flex', alignItems:'center', justifyContent:'center', color:'var(--text-secondary)', fontSize:13 }}>No photos available</div>
        )}
        <button onClick={onClose} style={{ position:'absolute', top:10, left:10, background:'rgba(255,255,255,0.9)', border:'none', borderRadius:'50%', width:32, height:32, cursor:'pointer', fontSize:18, display:'flex', alignItems:'center', justifyContent:'center' }}>×</button>
      </div>

      {/* Details body */}
      <div style={{ padding:'1.25rem', flex:1 }}>

        {/* Name + rating */}
        <div style={{ marginBottom:'1rem' }}>
          <h2 style={{ fontSize:'1.3rem', marginBottom:6 }}>{stop.name}</h2>
          <div style={{ display:'flex', gap:10, alignItems:'center', flexWrap:'wrap' }}>
            {details?.rating > 0 && (
              <span style={{ fontSize:13, color:'var(--accent)', fontWeight:500 }}>★ {details.rating} <span style={{ color:'var(--text-secondary)', fontWeight:400 }}>({details.total_ratings?.toLocaleString()})</span></span>
            )}
            {details?.price_level && PRICE[details.price_level] && (
              <span style={{ fontSize:13, color:'var(--text-secondary)' }}>{PRICE[details.price_level]}</span>
            )}
            {details?.open_now !== null && details?.open_now !== undefined && (
              <span style={{ fontSize:12, padding:'2px 8px', borderRadius:20, background:details.open_now?'var(--accent-light)':'#fdecea', color:details.open_now?'var(--accent)':'var(--danger)' }}>
                {details.open_now ? 'Open now' : 'Closed'}
              </span>
            )}
          </div>
        </div>

        {/* Editorial summary */}
        {details?.summary && (
          <p style={{ fontSize:13, color:'var(--text-secondary)', lineHeight:1.6, marginBottom:'1rem', padding:'0.75rem', background:'var(--bg)', borderRadius:8 }}>
            {details.summary}
          </p>
        )}

        {/* Info rows */}
        <div style={{ display:'flex', flexDirection:'column', gap:8, marginBottom:'1rem' }}>
          {details?.address && (
            <div style={{ display:'flex', gap:10, fontSize:13 }}>
              <span style={{ color:'var(--text-secondary)', width:20, textAlign:'center' }}>📍</span>
              <span>{details.address}</span>
            </div>
          )}
          {details?.phone && (
            <div style={{ display:'flex', gap:10, fontSize:13 }}>
              <span style={{ color:'var(--text-secondary)', width:20, textAlign:'center' }}>📞</span>
              <a href={`tel:${details.phone}`} style={{ color:'var(--accent)', textDecoration:'none' }}>{details.phone}</a>
            </div>
          )}
          {details?.website && (
            <div style={{ display:'flex', gap:10, fontSize:13 }}>
              <span style={{ color:'var(--text-secondary)', width:20, textAlign:'center' }}>🌐</span>
              <a href={details.website} target="_blank" rel="noreferrer" style={{ color:'var(--accent)', textDecoration:'none', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                {details.website.replace(/^https?:\/\//, '').replace(/\/$/, '')}
              </a>
            </div>
          )}
        </div>

        {/* Opening hours */}
        {details?.hours?.length > 0 && (
          <div style={{ marginBottom:'1rem' }}>
            <p style={{ fontSize:11, fontWeight:500, color:'var(--text-secondary)', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:8 }}>Hours</p>
            {details.hours.map((h, i) => (
              <div key={i} style={{ display:'flex', justifyContent:'space-between', fontSize:12, padding:'4px 0', borderBottom:'1px solid var(--border)', color:'var(--text-secondary)' }}>
                <span>{h.split(': ')[0]}</span>
                <span>{h.split(': ')[1] || ''}</span>
              </div>
            ))}
          </div>
        )}

        {/* Types */}
        {details?.types?.length > 0 && (
          <div style={{ display:'flex', gap:4, flexWrap:'wrap', marginBottom:'1rem' }}>
            {details.types.slice(0,6).map(t => (
              <span key={t} style={{ fontSize:10, padding:'2px 8px', borderRadius:12, background:'var(--bg)', border:'1px solid var(--border)', color:'var(--text-secondary)', textTransform:'capitalize' }}>
                {t.replace(/_/g,' ')}
              </span>
            ))}
          </div>
        )}

        {/* Action buttons */}
        <button onClick={onRemove} style={{ width:'100%', padding:'8px', background:'none', border:'1px solid var(--border)', borderRadius:8, fontFamily:'DM Sans,sans-serif', fontSize:13, color:'var(--danger)', cursor:'pointer', marginBottom:16 }}>
          Remove this stop
        </button>

        {/* Alternatives */}
        {alternatives?.length > 0 && (
          <div>
            <p style={{ fontSize:11, fontWeight:500, color:'var(--text-secondary)', textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:10 }}>Nearby alternatives</p>
            {alternatives.map(alt => (
              <div key={alt.place_id} style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'10px 0', borderBottom:'1px solid var(--border)' }}>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ fontSize:13, fontWeight:500, marginBottom:2 }}>{alt.name}</p>
                  <p style={{ fontSize:11, color:'var(--text-secondary)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{alt.address}</p>
                  {alt.rating > 0 && <p style={{ fontSize:11, color:'var(--accent)', marginTop:2 }}>★ {alt.rating}</p>}
                </div>
                <button onClick={() => onSwap(alt)} style={{ marginLeft:12, padding:'5px 12px', flexShrink:0, background:'var(--accent-light)', color:'var(--accent)', border:'1px solid var(--accent)', borderRadius:8, fontFamily:'DM Sans,sans-serif', fontSize:12, cursor:'pointer' }}>
                  Swap in
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Stop Card ────────────────────────────────────────────────────
function StopCard({ stop, index, included, expanded, onToggle, onExpand }) {
  return (
    <div style={{ padding:'0.875rem 1.25rem', background:included?'var(--accent-light)':'var(--surface)', border:`1.5px solid ${included?'var(--accent)':'var(--border)'}`, borderRadius:'var(--radius)', marginBottom:4, opacity:included?1:0.55, transition:'all 0.15s' }}>
      <div style={{ display:'flex', alignItems:'flex-start', gap:12 }}>
        <div onClick={onToggle} title={included?'Click to exclude':'Click to include'} style={{ width:28, height:28, borderRadius:'50%', background:included?'var(--accent)':'var(--border)', color:included?'#fff':'var(--text-secondary)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:12, fontWeight:500, flexShrink:0, marginTop:2, cursor:'pointer', userSelect:'none' }}>
          {included ? index + 1 : '–'}
        </div>
        <div style={{ flex:1, minWidth:0 }}>
          <p style={{ fontWeight:500, fontSize:14, marginBottom:1 }}>{stop.name}</p>
          <p style={{ fontSize:11, color:'var(--text-secondary)', overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>{stop.address}</p>
          {stop.rating > 0 && <p style={{ fontSize:11, color:'var(--accent)', marginTop:3 }}>★ {stop.rating}</p>}
        </div>
        <button onClick={onExpand} style={{ background:expanded?'var(--accent-light)':'none', border:`1px solid ${expanded?'var(--accent)':'var(--border)'}`, borderRadius:8, padding:'4px 8px', cursor:'pointer', fontSize:11, color:expanded?'var(--accent)':'var(--text-secondary)', fontFamily:'DM Sans,sans-serif', flexShrink:0 }}>
          {expanded ? 'Close' : 'Details'}
        </button>
      </div>
    </div>
  )
}

// ── Travel Badge ─────────────────────────────────────────────────
function TravelBadge({ travel }) {
  if (!travel) return null
  return (
    <div style={{ display:'flex', alignItems:'center', gap:6, padding:'4px 12px', margin:'2px 0 2px 40px', fontSize:11, color:'var(--text-secondary)' }}>
      <div style={{ width:1, height:16, background:'var(--border)', marginRight:4 }} />
      {travel.duration_text} · {travel.distance_text}
    </div>
  )
}

// ── Results Screen ───────────────────────────────────────────────
function ResultsScreen({ intent, itinerary: init, alternatives: initAlts, travelTimes: initTravel, directionsPath: initPath, mode, onReset, onExport, exporting, exported }) {
  const [stops,        setStops]        = useState(init.map(s => ({ ...s, included: true })))
  const [alternatives, setAlternatives] = useState(initAlts || {})
  const [travelTimes,  setTravelTimes]  = useState(initTravel || [])
  const [routePath,    setRoutePath]    = useState(initPath || [])
  const [expandedId,   setExpandedId]   = useState(null)
  const [selectedStop, setSelectedStop] = useState(null)
  const [date,         setDate]         = useState(intent.date || '')
  const [timeStart,    setTimeStart]    = useState(intent.time_start || '10:00')
  const [visitDur,     setVisitDur]     = useState(60)
  const [showExport,   setShowExport]   = useState(false)
  const [recalcing,    setRecalcing]    = useState(false)

  const includedStops = stops.filter(s => s.included)

  // Recalculate travel times + route whenever included stops change
async function recalculate(newStops) {
  const included = newStops.filter(s => s.included)
  if (included.length < 2) {
    setTravelTimes([])
    setRoutePath(included.map(s => ({ lat: s.lat, lng: s.lng })))
    return
  }
  setRecalcing(true)
  try {
    const res = await axios.post(`${API}/api/recalculate`, { stops: included, mode })
    setTravelTimes(res.data.travel_times)
    setRoutePath(res.data.directions_path)
  } catch (e) {
    console.error('Recalculate failed', e)
    // Keep the straight-line fallback that was set before this call
  } finally {
    setRecalcing(false)
  }
}

function toggleInclude(placeId) {
  const next = stops.map(s => s.place_id === placeId ? { ...s, included: !s.included } : s)
  setStops(next)
  setRoutePath(next.filter(s => s.included).map(s => ({ lat: s.lat, lng: s.lng })))
  recalculate(next)
}

function removeStop(placeId) {
  const next = stops.filter(s => s.place_id !== placeId)
  setStops(next)
  setAlternatives(prev => { const n = { ...prev }; delete n[placeId]; return n })
  setExpandedId(null)
  // Reset route immediately so old line disappears right away
  setRoutePath(next.filter(s => s.included).map(s => ({ lat: s.lat, lng: s.lng })))
  recalculate(next)
}

function swapStop(originalId, replacement) {
  const original = stops.find(s => s.place_id === originalId)
  const next     = stops.map(s => s.place_id === originalId ? { ...replacement, included: true } : s)
  setStops(next)
  setAlternatives(prev => {
    const n = { ...prev }
    delete n[originalId]
    n[replacement.place_id] = (prev[originalId] || [])
      .filter(a => a.place_id !== replacement.place_id)
      .concat(original ? [original] : [])
      .slice(0, 3)
    return n
  })
  setExpandedId(null)
  // Reset route immediately to included stops straight lines, then recalculate roads
  setRoutePath(next.filter(s => s.included).map(s => ({ lat: s.lat, lng: s.lng })))
  recalculate(next)
}

  const center = includedStops.length > 0
    ? { lat: includedStops[0].lat, lng: includedStops[0].lng }
    : { lat: 40.7128, lng: -74.0060 }

  let includedIndex = 0

  return (
    <div style={{ display:'flex', height:'100vh', overflow:'hidden' }}>

      {/* Left panel */}
      <div style={{ width:380, flexShrink:0, background:'var(--bg)', borderRight:'1px solid var(--border)', display:'flex', flexDirection:'column', overflow:'hidden' }}>
        <div style={{ padding:'1.25rem 1.5rem', borderBottom:'1px solid var(--border)', background:'var(--surface)' }}>
          <button onClick={onReset} style={{ fontSize:12, color:'var(--text-secondary)', background:'none', border:'none', cursor:'pointer', padding:0, marginBottom:12 }}>← New search</button>
          <h2 style={{ fontSize:'1.4rem', marginBottom:4 }}>Your itinerary</h2>
          <p style={{ fontSize:13, color:'var(--text-secondary)' }}>
            {intent.location} · {includedStops.length} stops · {MODES.find(m => m.value === mode)?.label}
            {recalcing && <span style={{ marginLeft:8, color:'var(--accent)' }}>Updating route...</span>}
          </p>
          <p style={{ fontSize:11, color:'var(--text-secondary)', marginTop:4 }}>Click the number to include/exclude · Click Details for more info</p>
        </div>

        <div style={{ flex:1, overflowY:'auto', padding:'1rem 1.25rem' }}>
          {stops.map((stop, i) => {
            const isExpanded   = expandedId === stop.place_id
            const displayIndex = stop.included ? includedIndex++ : null
            const travelIdx    = includedStops.findIndex(s => s.place_id === stop.place_id)

            return (
              <div key={stop.place_id}>
                <StopCard
                  stop={stop} index={displayIndex ?? i}
                  included={stop.included} expanded={isExpanded}
                  onToggle={() => toggleInclude(stop.place_id)}
                  onExpand={() => setExpandedId(isExpanded ? null : stop.place_id)}
                />
                {stop.included && travelIdx >= 0 && travelIdx < travelTimes.length && (
                  <TravelBadge travel={travelTimes[travelIdx]} />
                )}
              </div>
            )
          })}
        </div>

        {/* Export */}
        <div style={{ padding:'1rem 1.25rem', borderTop:'1px solid var(--border)', background:'var(--surface)' }}>
          {includedStops.length === 0 ? (
            <p style={{ fontSize:13, color:'var(--text-secondary)', textAlign:'center' }}>No stops selected.</p>
          ) : !showExport ? (
            <button onClick={() => setShowExport(true)} style={{ width:'100%', padding:'0.75rem', background:'var(--accent)', color:'#fff', border:'none', borderRadius:'var(--radius)', fontFamily:'DM Sans,sans-serif', fontSize:14, fontWeight:500, cursor:'pointer' }}>
              Export {includedStops.length} stops to Google Calendar
            </button>
          ) : (
            <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
              <div style={{ display:'flex', gap:8 }}>
                <div style={{ flex:1 }}>
                  <label style={{ fontSize:11, color:'var(--text-secondary)', display:'block', marginBottom:4 }}>Date</label>
                  <input type="date" value={date} onChange={e => setDate(e.target.value)} style={{ width:'100%', padding:'6px 10px', border:'1px solid var(--border)', borderRadius:8, fontFamily:'DM Sans,sans-serif', fontSize:13, background:'var(--surface)', color:'var(--text-primary)' }} />
                </div>
                <div style={{ flex:1 }}>
                  <label style={{ fontSize:11, color:'var(--text-secondary)', display:'block', marginBottom:4 }}>Start time</label>
                  <input type="time" value={timeStart} onChange={e => setTimeStart(e.target.value)} style={{ width:'100%', padding:'6px 10px', border:'1px solid var(--border)', borderRadius:8, fontFamily:'DM Sans,sans-serif', fontSize:13, background:'var(--surface)', color:'var(--text-primary)' }} />
                </div>
              </div>
              <label style={{ fontSize:11, color:'var(--text-secondary)', display:'flex', alignItems:'center', gap:8 }}>
                Visit duration
                <select value={visitDur} onChange={e => setVisitDur(Number(e.target.value))} style={{ border:'1px solid var(--border)', borderRadius:8, padding:'4px 8px', fontFamily:'DM Sans,sans-serif', fontSize:13, background:'var(--surface)', color:'var(--text-primary)' }}>
                  {[30,45,60,90,120].map(n => <option key={n} value={n}>{n} min</option>)}
                </select>
              </label>
              <button onClick={() => onExport(includedStops, date, timeStart, travelTimes, visitDur)} disabled={exporting || !date}
                style={{ width:'100%', padding:'0.75rem', background:exporting||!date?'var(--border)':'var(--accent)', color:exporting||!date?'var(--text-secondary)':'#fff', border:'none', borderRadius:'var(--radius)', fontFamily:'DM Sans,sans-serif', fontSize:14, fontWeight:500, cursor:exporting||!date?'not-allowed':'pointer' }}>
                {exporting ? 'Exporting...' : exported ? '✓ Exported!' : 'Confirm export'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Map */}
      <div style={{ flex:1, position:'relative' }}>
        <LoadScript googleMapsApiKey={MAPS_KEY}>
          <GoogleMap mapContainerStyle={mapStyles} center={center} zoom={14} options={mapOptions}>
            <Polyline path={routePath} options={{ strokeColor:'#2d5a3d', strokeOpacity:0.85, strokeWeight:4, geodesic:true }} />
            {stops.map((stop) => {
              const idx = includedStops.findIndex(s => s.place_id === stop.place_id)
              return (
                <Marker key={stop.place_id}
                  position={{ lat: stop.lat, lng: stop.lng }}
                  opacity={stop.included ? 1 : 0.3}
                  label={stop.included ? { text: String(idx+1), color:'#fff', fontSize:'12px', fontWeight:'500' } : { text:'–', color:'#fff', fontSize:'12px' }}
                  onClick={() => setSelectedStop(selectedStop?.place_id === stop.place_id ? null : stop)}
                />
              )
            })}
            {selectedStop && (
              <InfoWindow position={{ lat: selectedStop.lat, lng: selectedStop.lng }} onCloseClick={() => setSelectedStop(null)}>
                <div style={{ fontFamily:'DM Sans,sans-serif', maxWidth:200 }}>
                  <p style={{ fontWeight:500, marginBottom:4 }}>{selectedStop.name}</p>
                  <p style={{ fontSize:12, color:'#666' }}>{selectedStop.address}</p>
                  {selectedStop.rating > 0 && <p style={{ fontSize:12, color:'#2d5a3d', marginTop:4 }}>★ {selectedStop.rating}</p>}
                </div>
              </InfoWindow>
            )}
          </GoogleMap>
        </LoadScript>
      </div>

      {/* Details slide-in panel */}
      {expandedId && (() => {
        const stop = stops.find(s => s.place_id === expandedId)
        if (!stop) return null
        return (
          <PlaceDetailPanel
            stop={stop}
            alternatives={alternatives[expandedId] || []}
            onSwap={alt => swapStop(expandedId, alt)}
            onRemove={() => removeStop(expandedId)}
            onClose={() => setExpandedId(null)}
          />
        )
      })()}
    </div>
  )
}

// ── Root ─────────────────────────────────────────────────────────
export default function App() {
  const [screen,    setScreen]    = useState('input')
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState(null)
  const [result,    setResult]    = useState(null)
  const [exporting, setExporting] = useState(false)
  const [exported,  setExported]  = useState(false)

  async function handlePlan(message, maxStops, mode) {
    setLoading(true); setError(null)
    try {
      const res = await axios.post(`${API}/api/plan`, { message, max_stops: maxStops, radius_meters: 5000, mode })
      setResult(res.data); setScreen('results')
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.')
    } finally { setLoading(false) }
  }

  async function handleExport(itinerary, date, timeStart, travelTimes, visitDuration) {
    setExporting(true)
    try {
      await axios.post(`${API}/api/export`, { itinerary, date, time_start: timeStart, travel_times: travelTimes, visit_duration_min: visitDuration })
      setExported(true)
    } catch (err) {
      alert(err.response?.data?.detail || 'Export failed. Make sure you are logged in via /auth/login.')
    } finally { setExporting(false) }
  }

  return (
    <>
      {error && (
        <div style={{ position:'fixed', top:16, left:'50%', transform:'translateX(-50%)', background:'#fff', border:'1px solid var(--border)', borderLeft:'3px solid var(--danger)', padding:'0.75rem 1.25rem', borderRadius:'var(--radius)', fontSize:13, color:'var(--danger)', zIndex:1000, boxShadow:'var(--shadow)', maxWidth:400 }}>
          {error}
        </div>
      )}
      {screen === 'input' && <InputScreen onSubmit={handlePlan} loading={loading} />}
      {screen === 'results' && result && (
        <ResultsScreen
          intent={result.intent} itinerary={result.itinerary}
          alternatives={result.alternatives || {}}
          travelTimes={result.travel_times || []}
          directionsPath={result.directions_path || []}
          mode={result.mode || 'walking'}
          onReset={() => { setScreen('input'); setResult(null); setExported(false) }}
          onExport={handleExport} exporting={exporting} exported={exported}
        />
      )}
    </>
  )
}