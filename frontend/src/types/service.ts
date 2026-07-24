import type { ServiceIconType } from "../components/ServiceIcon";

export interface ServiceField {
  id: string;
  label: string;
  type: "text" | "number" | "date" | "select";
  required: boolean;
  options?: string[];
  hint?: string;
  placeholder?: string;
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
