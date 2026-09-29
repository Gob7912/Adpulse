import { Activity, Users, MessageCircle, Eye, BarChart3, LucideIcon } from 'lucide-react';

/**
 * Returns a lean Lucide icon component per report template/type:
 * - Ежедневный пульс: Activity
 * - Лидогенерация: Users
 * - Личные сообщения: MessageCircle
 * - Узнаваемость: Eye
 * - Custom / neutral: BarChart3
 */
export function getReportTypeIcon(
  typeOrId?: string | null,
  options?: {
    metrics?: string[];
    goals?: string[];
  }
): LucideIcon {
  const id = (typeOrId || '').toLowerCase();

  if (id === 'daily_pulse' || id === 'pulse') return Activity;
  if (id === 'lead_generation' || id === 'leads') return Users;
  if (id === 'direct_messages' || id === 'messages') return MessageCircle;
  if (id === 'brand_awareness' || id === 'awareness') return Eye;

  // Infer from campaign filter goals if available
  if (options?.goals && options.goals.length > 0) {
    const goalsUpper = options.goals.map((g) => String(g).toUpperCase());
    if (goalsUpper.some((g) => g.includes('LEAD'))) return Users;
    if (goalsUpper.some((g) => g.includes('MESSAGE'))) return MessageCircle;
    if (goalsUpper.some((g) => g.includes('AWARENESS') || g.includes('REACH'))) return Eye;
  }

  // Infer from metrics
  if (options?.metrics && options.metrics.length > 0) {
    if (options.metrics.includes('leads') || options.metrics.includes('cpl')) return Users;
    if (options.metrics.includes('messages') || options.metrics.includes('cost_per_dm')) return MessageCircle;
    if (
      options.metrics.includes('reach') &&
      options.metrics.includes('impressions') &&
      !options.metrics.includes('leads') &&
      !options.metrics.includes('messages')
    ) {
      return Eye;
    }
    if (options.metrics.includes('new_followers')) return Activity;
  }

  // Neutral icon for custom selections
  return BarChart3;
}
