import { ExplorerClient } from "@/components/data-products/data-product-clients";
export default async function Page({params}:{params:Promise<{workspaceId:string;projectId:string;datasetId:string}>}){const values=await params;return <ExplorerClient {...values}/>}
