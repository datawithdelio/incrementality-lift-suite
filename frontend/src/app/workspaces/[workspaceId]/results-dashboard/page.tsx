import { DashboardClient } from "@/components/measurement/measurement-clients";
export default async function Page({params}:{params:Promise<{workspaceId:string}>}){const {workspaceId}=await params;return <DashboardClient workspaceId={workspaceId}/>}
