import { MarketReactionDashboard } from "../components/MarketReactionDashboard";
import "./mri.css";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export default async function MarketReactionPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  return <MarketReactionDashboard params={await searchParams} />;
}
