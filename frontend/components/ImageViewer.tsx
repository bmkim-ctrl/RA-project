'use client';

import type { CSSProperties } from 'react';
import { useEffect, useRef, useState } from 'react';

import { PatientImage, ViewerMode, apiClient } from '@/services/api';

export function ImageViewer({
  patientId,
  images,
  selectedIndex,
  mode,
  onModeChange,
  onNavigate,
}: {
  patientId: string | null;
  images: PatientImage[];
  selectedIndex: number;
  mode: ViewerMode;
  onModeChange: (mode: ViewerMode) => void;
  onNavigate: (direction: 'prev' | 'next') => void;
}) {
  const image = images[selectedIndex];
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  }, [selectedIndex, mode]);

  const originalUrl = patientId && image ? apiClient.getImageUrl(patientId, image.filename) : '';

  return (
    <section style={panelStyle}>
      <div style={toolbarStyle}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {(['original', 'detection', 'gradcam', 'overlay'] as ViewerMode[]).map(item => (
            <button
              key={item}
              onClick={() => onModeChange(item)}
              style={{
                ...modeButtonStyle,
                background: item === mode ? 'rgba(53, 140, 173, 0.4)' : 'rgba(53, 140, 173, 0.18)',
                borderColor: item === mode ? '#4fb0d4' : 'rgba(79, 176, 212, 0.22)',
              }}
            >
              {item === 'gradcam' ? 'Grad-CAM' : item[0].toUpperCase() + item.slice(1)}
            </button>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => onNavigate('prev')} style={navButtonStyle}>Prev</button>
          <button onClick={() => onNavigate('next')} style={navButtonStyle}>Next</button>
          <button onClick={() => { setScale(1); setOffset({ x: 0, y: 0 }); }} style={navButtonStyle}>Reset</button>
        </div>
      </div>

      <div
        style={viewportStyle}
        onWheel={event => {
          event.preventDefault();
          setScale(current => Math.min(4, Math.max(0.75, current - event.deltaY * 0.0012)));
        }}
        onMouseDown={event => {
          dragRef.current = { x: event.clientX - offset.x, y: event.clientY - offset.y };
        }}
        onMouseMove={event => {
          if (!dragRef.current) {
            return;
          }
          setOffset({ x: event.clientX - dragRef.current.x, y: event.clientY - dragRef.current.y });
        }}
        onMouseUp={() => {
          dragRef.current = null;
        }}
        onMouseLeave={() => {
          dragRef.current = null;
        }}
      >
        {!image ? (
          <div style={{ color: 'var(--muted)' }}>Select a patient study to review images.</div>
        ) : (
          <div
            style={{
              position: 'relative',
              transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
              transition: dragRef.current ? 'none' : 'transform 120ms ease',
            }}
          >
            <img src={originalUrl} alt={image.filename} style={imageStyle} />
            {mode === 'detection' && image.detection_image && <img src={image.detection_image} alt="" style={overlayImageStyle} />}
            {mode === 'gradcam' && image.gradcam_image && <img src={image.gradcam_image} alt="" style={overlayImageStyle} />}
            {mode === 'overlay' && (
              <>
                {image.detection_image && <img src={image.detection_image} alt="" style={{ ...overlayImageStyle, opacity: 0.6 }} />}
                {image.gradcam_image && (
                  <img
                    src={image.gradcam_image}
                    alt=""
                    style={{ ...overlayImageStyle, opacity: 0.4, mixBlendMode: 'screen' }}
                  />
                )}
              </>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

const panelStyle: CSSProperties = {
  background: '#030608',
  border: '1px solid #16435a',
  borderRadius: 0,
  padding: 12,
  height: '100%',
  minHeight: 0,
  display: 'grid',
  gridTemplateRows: 'auto 1fr',
  gap: 10,
};

const toolbarStyle: CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: 8,
  flexWrap: 'wrap',
};

const viewportStyle: CSSProperties = {
  border: '1px solid #16435a',
  background: '#000',
  overflow: 'hidden',
  display: 'grid',
  placeItems: 'center',
  minHeight: 0,
  height: '100%',
};

const imageStyle: CSSProperties = {
  maxWidth: '100%',
  maxHeight: 560,
  display: 'block',
  objectFit: 'contain',
};

const overlayImageStyle: CSSProperties = {
  position: 'absolute',
  inset: 0,
  width: '100%',
  height: '100%',
  objectFit: 'contain',
};

const modeButtonStyle: CSSProperties = {
  padding: '8px 12px',
  borderRadius: 0,
  border: '1px solid #16435a',
  color: '#e7edf7',
  fontSize: 12,
};

const navButtonStyle: CSSProperties = {
  padding: '8px 12px',
  borderRadius: 0,
  border: '1px solid #16435a',
  background: '#123f57',
  color: '#f6fbff',
  fontSize: 12,
};
