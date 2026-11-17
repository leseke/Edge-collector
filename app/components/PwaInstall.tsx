"use client";
import { useEffect, useState } from "react";

type InstallPrompt = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> };
export function PwaInstall() {
  const [prompt, setPrompt] = useState<InstallPrompt | null>(null);
  const [ios, setIos] = useState(false);
  const [standalone, setStandalone] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {});
    }
    const installed = window.matchMedia("(display-mode: standalone)").matches || (navigator as Navigator & { standalone?: boolean }).standalone === true;
    setStandalone(installed);
    setIos(/iPad|iPhone|iPod/.test(navigator.userAgent));
    const onPrompt = (event: Event) => { event.preventDefault(); setPrompt(event as InstallPrompt); };
    const onInstalled = () => { setStandalone(true); setPrompt(null); setShowHelp(false); };
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => { window.removeEventListener("beforeinstallprompt", onPrompt); window.removeEventListener("appinstalled", onInstalled); };
  }, []);
  if (standalone) return null;
  return <div className="pwa-install">
    <button type="button" onClick={async () => {
      if (prompt) { await prompt.prompt(); await prompt.userChoice; setPrompt(null); }
      else setShowHelp((value) => !value);
    }} aria-expanded={showHelp}>Installer EDGE <span aria-hidden="true">↗</span></button>
    {showHelp && <p role="status">{ios ? "Sur iPhone : ouvrez EDGE dans Safari, touchez Partager puis « Sur l’écran d’accueil »." : "Dans votre navigateur, ouvrez le menu puis choisissez « Installer l’application » ou « Ajouter à l’écran d’accueil », si proposé."}</p>}
  </div>;
}
