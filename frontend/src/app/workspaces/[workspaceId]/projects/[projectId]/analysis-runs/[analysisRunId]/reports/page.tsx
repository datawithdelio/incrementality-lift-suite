import { ReportsClient } from "@/components/data-products/data-product-clients";
export default async function Page({params}:{params:Promise<{workspaceId:string;projectId:string;analysisRunId:string}>}){const {workspaceId,projectId,analysisRunId}=await params;return <ReportsClient workspaceId={workspaceId} projectId={projectId} runId={analysisRunId}/>}
