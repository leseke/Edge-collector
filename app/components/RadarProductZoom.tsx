"use client";

import { createContext, useContext, useEffect, useId, useRef, useState, type ReactNode } from "react";

const ExpandedImage = createContext(false);

export function GccProductImage({ src, name }: { src: string; name: string }) {
  const expanded = useContext(ExpandedImage);
  const [useThumbnail, setUseThumbnail] = useState(false);
  const full = src.replace("/width=300,fit=contain,format=webp,quality=65/", "/width=1000,fit=contain,format=webp,quality=85/");
  return <img src={expanded && !useThumbnail ? full : src} alt={name}
    loading={expanded ? "eager" : "lazy"} onError={() => setUseThumbnail(true)} />;
}

export function RadarProductZoom({ name, children, details }: { name: string; children: ReactNode; details?: ReactNode }) {
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const trigger = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal();
  }, [open]);

  return <>
    <article className="radar-sale-card radar-zoom-card">
      {children}
      <button ref={trigger} className="radar-zoom-trigger" type="button" aria-label={`Agrandir la fiche de ${name}`}
        aria-haspopup="dialog" onClick={() => setOpen(true)}>Voir la fiche <span aria-hidden="true">↗</span></button>
    </article>
    {open && <dialog ref={dialog} className="radar-zoom-dialog" aria-labelledby={titleId}
      onClose={() => { setOpen(false); trigger.current?.focus(); }} onClick={event => {
        if (event.target === event.currentTarget) dialog.current?.close();
      }}>
      <div className="radar-zoom-content">
        <header><div><small className="radar-zoom-eyebrow">EDGE · FICHE PRODUIT</small><strong id={titleId}>{name}</strong></div>
          <button autoFocus type="button" onClick={() => dialog.current?.close()}>Fermer</button>
        </header>
        <ExpandedImage.Provider value={true}><div className="radar-zoom-detail">{children}</div></ExpandedImage.Provider>
        {details && <div className="radar-zoom-evidence">{details}</div>}
      </div>
    </dialog>}
  </>;
}
