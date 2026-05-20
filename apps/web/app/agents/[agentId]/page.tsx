import { AgentDetail } from "./agent-detail";

type AgentDetailPageProps = {
  params: Promise<{
    agentId: string;
  }>;
};

export default async function AgentDetailPage({
  params
}: AgentDetailPageProps) {
  const { agentId } = await params;

  return <AgentDetail agentId={agentId} />;
}
