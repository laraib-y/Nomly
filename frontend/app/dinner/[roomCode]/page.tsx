import { Lobby } from "@/components/Lobby";

export default async function DinnerPage({ params }: { params: Promise<{ roomCode: string }> }) {
  const { roomCode } = await params;
  return <Lobby roomCode={roomCode} />;
}
