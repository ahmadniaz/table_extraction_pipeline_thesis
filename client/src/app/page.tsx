import { redirect } from 'next/navigation';

/** Default landing: batch evaluation hub (pick tools / documents). Corpus remains in nav. */
export default function HomePage() {
  redirect('/evaluation');
}
