import { AgentGovernanceForm } from "../../agent-governance-form";

type EditAgentPageProps = {
  params: Promise<{
    agentId: string;
  }>;
};

export default async function EditAgentPage({ params }: EditAgentPageProps) {
  const { agentId } = await params;
  return <AgentGovernanceForm agentId={agentId} mode="edit" />;
}
