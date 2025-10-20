// List of authorized email addresses for testing period
const AUTHORIZED_EMAILS = [
  'shaine.rucker@pinecrestconsulting.com',
  'david.almeida@innovativebps.com',
  'muhammad@pinecrestconsulting.com',
  'sales@pinecrestconsulting.com'
];

/**
 * Check if an email is in the authorized list
 * @param email - The email address to check
 * @returns true if email is authorized, false otherwise
 */
export function isEmailAuthorized(email: string): boolean {
  return AUTHORIZED_EMAILS.includes(email.toLowerCase().trim());
}

/**
 * Get the list of authorized emails (for display purposes)
 * @returns Array of authorized email addresses
 */
export function getAuthorizedEmails(): string[] {
  return [...AUTHORIZED_EMAILS];
}
