export const dynamic = "force-dynamic";
export function GET() {
 return Response.json({application:"EDGE",design:"v3",revision:process.env.NEXT_PUBLIC_EDGE_REVISION ?? "unknown"},{headers:{"Cache-Control":"no-store"}});
}
