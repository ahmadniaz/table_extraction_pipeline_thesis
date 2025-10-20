interface CompanySuffixMapping {
  [key: string]: string;
}

interface NormalizedCompany {
  originalName: string;
  normalizedName: string;
  canonicalName: string;
  carriers: string[];
  duplicateGroup?: string;
}

class CompanyNameNormalizer {
  private static suffixMappings: CompanySuffixMapping = {
    // Limited Liability Company variations
    'llc': 'LLC',
    'l.l.c.': 'LLC',
    'l.l.c': 'LLC',
    'll': 'LLC',
    'limited liability company': 'LLC',
    'limited liability co.': 'LLC',
    'limited liability co': 'LLC',
    
    // Corporation variations
    'inc': 'Inc.',
    'inc.': 'Inc.',
    'incorporated': 'Inc.',
    'corporation': 'Corp.',
    'corp': 'Corp.',
    'corp.': 'Corp.',
    'cor': 'Corp.', // Handle truncated "Corp"
    
    // Limited variations
    'ltd': 'Ltd.',
    'ltd.': 'Ltd.',
    'limited': 'Ltd.',
    
    // Company variations
    'co': 'Co.',
    'co.': 'Co.',
    'company': 'Co.',
    
    // Professional services
    'pllc': 'PLLC',
    'p.l.l.c.': 'PLLC',
    'professional llc': 'PLLC',
    
    // Partnerships
    'llp': 'LLP',
    'l.l.p.': 'LLP',
    'limited liability partnership': 'LLP',
    
    // Other forms
    'lp': 'LP',
    'l.p.': 'LP',
    'limited partnership': 'LP'
  };

  // All suffix variations for stripping (lowercase)
  private static allSuffixVariations = new Set([
    'llc', 'l.l.c.', 'l.l.c', 'll', 'limited liability company', 'limited liability co.', 'limited liability co',
    'inc', 'inc.', 'incorporated', 'corporation', 'corp', 'corp.', 'cor',
    'ltd', 'ltd.', 'limited',
    'co', 'co.', 'company',
    'pllc', 'p.l.l.c.', 'professional llc',
    'llp', 'l.l.p.', 'limited liability partnership',
    'lp', 'l.p.', 'limited partnership'
  ]);

  // Common business words that should be separated when concatenated
  private static businessWords = new Set([
    'logistics', 'transport', 'shipping', 'delivery', 'freight', 'cargo',
    'express', 'global', 'international', 'services', 'solutions', 'group',
    'companies', 'corporation', 'enterprises', 'industries', 'systems',
    'trucking', 'hauling', 'moving', 'storage', 'warehouse', 'distribution',
    'couriers', 'courier', 'box'
  ]);

  private static commonRemovals = new Set([
    'the', 'of', 'and', '&', 'at', 'in', 'on', 'for', 'to', 'a', 'an'
  ]);

  /**
   * Get the core company name without legal suffix for matching purposes
   * This allows "Alco Logistics" and "Alco Logistics LLC" to be treated as the same
   */
  static getCoreName(companyName: string): string {
    if (!companyName?.trim()) return companyName;
    
    let name = companyName.trim().toLowerCase();
    
    // Remove punctuation and normalize spaces
    name = name.replace(/[,._-]/g, ' ').replace(/\s+/g, ' ').trim();
    
    // Sort suffixes by length (longest first) for better matching
    const sortedSuffixes = Array.from(this.allSuffixVariations).sort((a, b) => b.length - a.length);
    
    // Remove suffix if present at the end
    for (const suffix of sortedSuffixes) {
      // Check if name ends with this suffix (as a whole word or concatenated)
      if (name.endsWith(' ' + suffix)) {
        name = name.substring(0, name.length - suffix.length - 1).trim();
        break;
      } else if (name.endsWith(suffix) && name.length > suffix.length) {
        // Check if it's concatenated (no space)
        const beforeSuffix = name.substring(0, name.length - suffix.length);
        if (beforeSuffix.length > 0 && beforeSuffix[beforeSuffix.length - 1] !== ' ') {
          name = beforeSuffix.trim();
          break;
        }
      }
    }
    
    return name.trim();
  }

  static normalize(companyName: string): string {
    if (!companyName?.trim()) return companyName;
    
    const originalName = companyName;
    let name = companyName.trim();
    
    // Step 1: Basic cleanup
    name = name.replace(/\s+/g, ' ');
    name = name.replace(/[,._-]/g, ' ')
               .replace(/&/g, ' and ')
               .replace(/\+/g, ' and ');
    
    // Step 2: Handle concatenated business words
    const nameLower = name.toLowerCase();
    let processedName = name;
    
    // Check for concatenated business words and separate them
    for (const word of this.businessWords) {
      // Pattern: letters/numbers + businessword + optional letters
      const pattern = new RegExp(`([a-zA-Z0-9]+)(${word})([a-zA-Z]*)`, 'gi');
      const match = pattern.exec(nameLower);
      if (match && match[1].length > 0) {
        const before = match[1];
        const businessWord = word;
        const after = match[3] || '';
        
        // Reconstruct with proper spacing
        let replacement = before + ' ' + businessWord;
        if (after) {
          replacement += ' ' + after;
        }
        
        // Replace in the original name (preserving case structure)
        const originalMatch = new RegExp(`([a-zA-Z0-9]+)(${word})([a-zA-Z]*)`, 'i').exec(processedName);
        if (originalMatch) {
          const beforeOriginal = originalMatch[1];
          const afterOriginal = originalMatch[3] || '';
          let newReplacement = beforeOriginal + ' ' + businessWord.charAt(0).toUpperCase() + businessWord.slice(1);
          if (afterOriginal) {
            newReplacement += ' ' + afterOriginal;
          }
          processedName = processedName.replace(originalMatch[0], newReplacement);
        }
      }
    }
    
    // Step 3: Handle concatenated suffixes
    const lowerName = processedName.toLowerCase().trim();
    let suffix = '';
    let mainName = lowerName;
    
    // Check for concatenated suffixes (sorted by length, longest first)
    const sortedSuffixes = Object.entries(this.suffixMappings).sort((a, b) => b[0].length - a[0].length);
    
    for (const [suffixKey, suffixValue] of sortedSuffixes) {
      if (lowerName.endsWith(suffixKey) && suffixKey.length > 1) {
        const suffixStart = lowerName.length - suffixKey.length;
        
        // Check if it's truly concatenated (no space before suffix)
        if (suffixStart > 0 && lowerName[suffixStart - 1] !== ' ') {
          mainName = lowerName.substring(0, suffixStart);
          suffix = suffixValue;
          break;
        }
      }
    }
    
    // Step 4: Split into words and process
    const parts = mainName.split(' ').filter(p => p.length > 0);
    
    // Step 5: If no concatenated suffix found, check for separated suffix
    if (!suffix && parts.length > 0) {
      // Check last 3 words for legal suffixes
      for (let i = Math.max(0, parts.length - 3); i < parts.length; i++) {
        const potentialSuffix = parts.slice(i).join(' ');
        if (this.suffixMappings[potentialSuffix]) {
          suffix = this.suffixMappings[potentialSuffix];
          parts.splice(i); // Remove suffix parts
          break;
        }
      }
    }
    
    // Step 6: Clean and format main parts
    const cleanedParts = parts
      .filter(part => !this.commonRemovals.has(part) && part.length > 0)
      .map(part => {
        // Handle special cases like "A1", "2C", etc.
        if (/^[0-9]+[a-zA-Z]+$/.test(part) || /^[a-zA-Z][0-9]+$/.test(part)) {
          return part.toUpperCase();
        }
        // Handle mixed alphanumeric that should stay together
        if (/^[a-zA-Z0-9]+$/.test(part) && part.length <= 4) {
          return part.charAt(0).toUpperCase() + part.slice(1).toLowerCase();
        }
        return part.charAt(0).toUpperCase() + part.slice(1).toLowerCase();
      });
    
    // Step 7: Reconstruct final name
    let result = cleanedParts.join(' ');
    if (suffix) {
      result += ` ${suffix}`;
    }
    
    return result.trim() || originalName; // Fallback to original
  }

  static calculateSimilarity(name1: string, name2: string): number {
    const norm1 = this.normalize(name1).toLowerCase();
    const norm2 = this.normalize(name2).toLowerCase();
    
    // Exact match after normalization
    if (norm1 === norm2) return 1.0;
    
    // CRITICAL: Compare core names (without suffixes)
    // This makes "Alco Logistics" and "Alco Logistics LLC" identical
    const core1 = this.getCoreName(name1);
    const core2 = this.getCoreName(name2);
    
    // If core names match exactly, they're the same company
    if (core1 === core2 && core1.length > 0) return 1.0;
    
    // Check if one core name is contained in the other (handles truncation)
    // e.g., "America Delivers Cor" vs "America Delivers Corp."
    // e.g., "Advanced Carrier Ser" vs "Advanced Carrier Services"
    if (core1.length > 0 && core2.length > 0) {
      const longer = core1.length > core2.length ? core1 : core2;
      const shorter = core1.length > core2.length ? core2 : core1;
      
      // If shorter is a prefix of longer, likely truncated
      if (longer.startsWith(shorter)) {
        const lengthDiff = longer.length - shorter.length;
        
        // Very short truncation (1-3 chars) - almost certainly the same company
        if (lengthDiff <= 3) {
          return 0.98;
        }
        // Medium truncation (4-10 chars) - likely same if shorter is substantial
        if (lengthDiff <= 10 && shorter.length >= 10) {
          return 0.95;
        }
        // Longer truncation - check if it's just a word ending
        if (lengthDiff <= 20 && shorter.length >= 15) {
          // Check if we're missing complete words
          const longerWords = longer.split(' ');
          const shorterWords = shorter.split(' ');
          if (shorterWords.length === longerWords.length - 1) {
            // Missing one word at the end
            return 0.90;
          }
        }
      }
      
      // Handle concatenated vs separated (e.g., "arccouriers" vs "arc couriers")
      const core1NoSpaces = core1.replace(/\s+/g, '');
      const core2NoSpaces = core2.replace(/\s+/g, '');
      if (core1NoSpaces === core2NoSpaces) {
        return 1.0; // Exact match when spaces ignored
      }
      
      // Handle partial word truncation (e.g., "ser" vs "services")
      // Check if all complete words in shorter match the beginning of longer
      const words1 = core1.split(' ').filter(w => w.length > 0);
      const words2 = core2.split(' ').filter(w => w.length > 0);
      
      if (words1.length > 0 && words2.length > 0) {
        const longerWords = words1.length > words2.length ? words1 : words2;
        const shorterWords = words1.length > words2.length ? words2 : words1;
        
        // Check if all shorter words match longer words in order
        let allMatch = true;
        for (let i = 0; i < shorterWords.length; i++) {
          if (i >= longerWords.length || !longerWords[i].startsWith(shorterWords[i])) {
            allMatch = false;
            break;
          }
        }
        
        if (allMatch && shorterWords.length >= 2) {
          // "advanced carrier ser" matches "advanced carrier services"
          return 0.92;
        }
      }
    }
    
    // Levenshtein distance similarity on core names
    const maxLen = Math.max(core1.length, core2.length);
    if (maxLen === 0) return 0;
    
    const distance = this.levenshteinDistance(core1, core2);
    const sequenceSimilarity = (maxLen - distance) / maxLen;
    
    // Jaccard similarity on words (using core names)
    const words1 = new Set(core1.split(' ').filter(w => w.length > 0));
    const words2 = new Set(core2.split(' ').filter(w => w.length > 0));
    const intersection = new Set([...words1].filter(x => words2.has(x)));
    const union = new Set([...words1, ...words2]);
    const jaccardSimilarity = union.size > 0 ? intersection.size / union.size : 0;
    
    // Boost similarity if one is clearly a shortened version of the other
    const shortSimilarityBoost = this.checkShortNameMatch(core1, core2);
    
    // Combined score with emphasis on Jaccard (word matching)
    const combinedScore = (sequenceSimilarity * 0.4) + (jaccardSimilarity * 0.5) + (shortSimilarityBoost * 0.1);
    
    return Math.min(1.0, combinedScore);
  }

  private static checkShortNameMatch(name1: string, name2: string): number {
    const shorter = name1.length < name2.length ? name1 : name2;
    const longer = name1.length < name2.length ? name2 : name1;
    
    // Check if shorter name is a prefix of longer name
    if (longer.startsWith(shorter) && longer.length - shorter.length <= 4) {
      return 0.3; // 30% boost
    }
    
    // Check if main words match (ignoring suffixes)
    const shorterWords = shorter.replace(/ (llc|inc|corp|ltd|co|lp|llp|pllc)$/i, '').split(' ');
    const longerWords = longer.replace(/ (llc|inc|corp|ltd|co|lp|llp|pllc)$/i, '').split(' ');
    
    if (shorterWords.length > 0 && longerWords.join(' ').includes(shorterWords.join(' '))) {
      return 0.2; // 20% boost
    }
    
    return 0;
  }

  private static levenshteinDistance(str1: string, str2: string): number {
    const matrix = Array(str2.length + 1).fill(null)
      .map(() => Array(str1.length + 1).fill(null));
    
    for (let i = 0; i <= str1.length; i++) matrix[0][i] = i;
    for (let j = 0; j <= str2.length; j++) matrix[j][0] = j;
    
    for (let j = 1; j <= str2.length; j++) {
      for (let i = 1; i <= str1.length; i++) {
        const indicator = str1[i - 1] === str2[j - 1] ? 0 : 1;
        matrix[j][i] = Math.min(
          matrix[j][i - 1] + 1,
          matrix[j - 1][i] + 1,
          matrix[j - 1][i - 1] + indicator
        );
      }
    }
    
    return matrix[str2.length][str1.length];
  }

  static groupSimilarCompanies(
    companies: { name: string; carriers: string[] }[], 
    threshold: number = 0.75  // Lower threshold with smarter core name matching
  ): Array<{ canonical: string; variations: Array<{ name: string; carriers: string[] }> }> {
    const processed = new Set<number>();
    const groups: Array<{ canonical: string; variations: Array<{ name: string; carriers: string[] }> }> = [];
    
    companies.forEach((company, i) => {
      if (processed.has(i)) return;
      
      const group = [company];
      processed.add(i);
      
      companies.forEach((otherCompany, j) => {
        if (j <= i || processed.has(j)) return;
        
        const similarity = this.calculateSimilarity(company.name, otherCompany.name);
        if (similarity >= threshold) {
          group.push(otherCompany);
          processed.add(j);
        }
      });
      
      if (group.length > 1) {
        // Choose the most complete/longest normalized name as canonical
        const canonical = group
          .map(g => this.normalize(g.name))
          .reduce((longest, current) => current.length > longest.length ? current : longest);
        groups.push({ canonical, variations: group });
      }
    });
    
    return groups;
  }
}

export { CompanyNameNormalizer, type NormalizedCompany };
