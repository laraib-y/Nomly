import { SwipeRoom } from "@/components/SwipeRoom";

export default async function SwipePage({ params }: { params: Promise<{ roomCode: string }> }) {
  const { roomCode } = await params;
  return <SwipeRoom roomCode={roomCode} />;
}
