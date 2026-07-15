export type DashboardRun = { run_id:string; project_id:string; project_name:string; status:string; estimator_type:string; method_label:string; metric_label:string; effect:number|null; confidence_low:number|null; confidence_high:number|null; reliability:string; business_impact:number|null; warnings:string[]; created_at:string; failure_reason:string|null };
export type DashboardResponse = { total_runs:number; succeeded_runs:number; failed_runs:number; active_runs:number; runs:DashboardRun[] };
export type Channel = { channel:string; spend:number|null; incremental_revenue:number|null; incremental_conversions:number|null; lift:number|null; incremental_roas:number|null; observed_roas:number|null; confidence_low:number|null; confidence_high:number|null; contribution:number|null; marginal_response:number|null; reliability:string; recommended_movement:string; warning:string };
export type ChannelResponse = { channels:Channel[] };
export type LoadState<T> = {kind:"loading"}|{kind:"permission"}|{kind:"error"}|{kind:"ready";data:T};
export type DashboardFilters = {projectId?:string; estimator?:string; status?:string; dateFrom?:string; dateTo?:string};
