import type { LegalSubject, LoginCredential, User } from './auth.types';

export const credentials: LoginCredential[] = [
  {
    email: 'jan@example.com',
    password: '123',
  },
  {
    email: 'anna@example.com',
    password: '123',
  },
];

export const users: User[] = [
  {
    id: 'user-001',
    credentialId: 'cred-001',
    firstName: 'Jan',
    lastName: 'Kowalski',
    createdAt: '2026-01-10T10:00:00Z',
    email: 'jan@example.com',
    password: '123',
  },
  {
    id: 'user-002',
    credentialId: 'cred-002',
    firstName: 'Anna',
    lastName: 'Nowak',
    createdAt: '2026-01-12T12:00:00Z',
    email: 'anna@example.com',
    password: '123',
  },
];

export const legalSubjects: LegalSubject[] = [
  {
    id: 'subject-001',
    subjectType: 'PERSON',
    name: 'Jan Kowalski',
    country: 'PL',
    pesel: '90010112345',
    dateOfBirth: '1990-01-01',
    createdAt: '2026-01-10T10:00:00Z',
  },
  {
    id: 'subject-002',
    subjectType: 'COMPANY',
    name: 'ABC Solutions Sp. z o.o.',
    country: 'PL',
    nip: '5250001009',
    regon: '012345678',
    krs: '0000123456',
    legalForm: 'SP_ZOO',
    createdAt: '2026-01-10T11:00:00Z',
  },
  {
    id: 'subject-003',
    subjectType: 'COMPANY',
    name: 'XYZ Consulting Sp. z o.o.',
    country: 'PL',
    nip: '5260001008',
    regon: '123456789',
    krs: '0000654321',
    legalForm: 'SP_ZOO',
    createdAt: '2026-01-12T12:00:00Z',
  },
];
