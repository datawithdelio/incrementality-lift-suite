export type LoadState<T>={kind:"loading"}|{kind:"permission"}|{kind:"error"}|{kind:"ready";data:T};
export type ColumnSummary={name:string;inferred_type:string;missing_percentage:number;unique_count:number;minimum:number|string|null;maximum:number|string|null;mean:number|null;median:number|null};
export type DatasetPreview={rows:Record<string,unknown>[];columns:ColumnSummary[];total_rows:number;page:number;page_size:number;total_pages:number;date_range:{column:string;minimum:string;maximum:string}|null;treatment_distribution:Record<string,number>;outcome_distribution:Record<string,number>};
export type QualityFinding={rule_id:string;severity:string;passed:boolean;evidence:Record<string,unknown>;recommendation:string};
export type DataQuality={score:number;ready:boolean;findings:QualityFinding[]};
export type ReportJob={id:string;version:number;format:string;status:string;attempt_count:number;max_attempts:number;failure_reason:string|null;created_at:string};
export type DatasetVersion={id:string;source_filename:string;checksum_sha256:string;row_count:number|null;created_at:string};
