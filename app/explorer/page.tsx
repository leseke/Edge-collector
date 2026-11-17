import { getTcgMarketSnapshot } from "../lib/market-data";
import { ExplorerGrid } from "./ExplorerGrid";
import "../dashboard.css";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export default async function ExplorerPage() {
  const snapshot = await getTcgMarketSnapshot();
  return <ExplorerGrid cards={snapshot.cards} warning={snapshot.warning} />;
}
