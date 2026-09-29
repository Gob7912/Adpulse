import { ru } from './ru';
import { uz } from './uz';
import { en } from './en';
import { Language } from '../types';

export const translations = {
  ru,
  uz,
  en,
};

export function getTranslation(lang: Language) {
  return translations[lang] || translations.ru;
}
