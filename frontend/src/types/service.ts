import type { ServiceIconType } from "../components/ServiceIcon";

export interface ServiceField {
  id: string;
  label: string;
  type: "text" | "textarea" | "number" | "date" | "time" | "select" | "file";
  required: boolean;
  options?: string[];
  /** number 欄位的最小值，未指定時為 1（不允許 0 與負數）。 */
  min?: number;
  /** number 欄位的級距，未指定時為 1（整數）。 */
  step?: number;
  hint?: string;
  placeholder?: string;
  minValue?: string;
  maxValue?: string;
  rows?: number;
  accept?: string;
  visibleWhen?: {
    fieldId: string;
    value: string;
  };
  sectionTitle?: string;
  inputIcon?: ServiceIconType;
}

export interface ServiceSchema {
  service_id: string;
  title: string;
  description: string;
  fields: ServiceField[];
}

export interface ServiceDefinition extends ServiceSchema {
  subtitle: string;
  icon: ServiceIconType;
}
