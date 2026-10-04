import { LoadingScreen } from "@/components/LoadingScreen";

export default async function LoadingPage({ params }: { params: Promise<{ roomCode: string }> }) {
  const { roomCode } = await params;
  return <LoadingScreen destination={`/dinner/${encodeURIComponent(roomCode)}`} />;
}