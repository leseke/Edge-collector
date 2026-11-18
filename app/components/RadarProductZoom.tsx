"use client";

import { useEffect, useId, useRef, useState, type ReactNode } from "react";

export function RadarProductZoom({ name, children }: { name: string; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    if (open && !dialog.current?.open) dialog.current?.showModal();
  }, [open]);

  return <>
    <article className="radar-sale-card radar-zoom-card">
      {children}
      <button className="radar-zoom-trigger" type="button" aria-label={`Agrandir la fiche de ${name}`}
        aria-haspopup="dialog" onClick={() => setOpen(true)}>Agrandir ↗</button>
    </article>
    {open && <dialog ref={dialog} className="radar-zoom-dialog" aria-labelledby={titleId}
      onClose={() => setOpen(false)} onClick={event => {
        if (event.target === event.currentTarget) dialog.current?.close();
      }}>
      <div className="radar-zoom-content">
        <header><strong id={titleId}>{name}</strong>
          <button autoFocus type="button" onClick={() => dialog.current?.close()}>Fermer</button>
        </header>
        <div className="radar-zoom-detail">{children}</div>
      </div>
    </dialog>}
  </>;
}
