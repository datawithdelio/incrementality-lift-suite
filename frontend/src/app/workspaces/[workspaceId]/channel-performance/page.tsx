import { ChannelClient } from "@/components/measurement/measurement-clients";
export default async function Page({params}:{params:Promise<{workspaceId:string}>}){const {workspaceId}=await params;return <ChannelClient workspaceId={workspaceId}/>}
