import { redirect } from 'next/navigation';

/** Default landing: document corpus (upload → ground truth → per-document evaluation). */
export default function HomePage() {
  redirect('/corpus');
}
