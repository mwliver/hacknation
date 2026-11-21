
export type UUID = string;

export type SubjectType = "PERSON" | "COMPANY";

export type CredentialStatus = "ACTIVE" | "BLOCKED";

export type UserStatus = "ACTIVE" | "INACTIVE";

export type SubjectRole = "OWNER" | "ADMIN" | "USER";

export interface LoginCredential {
  email: string;
  password: string;
}

export interface User {
  id: UUID;
  credentialId: UUID;
  firstName: string;
  lastName: string;
  createdAt: string;
  email: string;
  password: string;
}

export interface LegalSubject {
  id: UUID;
  subjectType: SubjectType;
  name: string;
  country: string;

  // Dane osoby fizycznej
  pesel?: string;
  dateOfBirth?: string;

  // Dane osoby prawnej
  nip?: string;
  regon?: string;
  krs?: string;
  legalForm?: string;

  createdAt: string;
}