import { ResultsRoom } from "@/components/ResultsRoom";

export default async function ResultsPage({ params }: { params: Promise<{ roomCode: string }> }) {
  const { roomCode } = await params;
  return <ResultsRoom roomCode={roomCode} />;
}
