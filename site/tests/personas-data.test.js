import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { personas, defaultPersona, lifecycle, composition } from '../src/lib/personas-data.js';

const siteRoot = join(import.meta.dirname, '..');
const repoRoot = join(siteRoot, '..');
const registryToml = readFileSync(join(repoRoot, 'pack', 'personas.toml'), 'utf8');

/** The persona ids declared in the pack registry (the source of truth). */
function registryIds() {
  return [...registryToml.matchAll(/^id = "([^"]+)"/gm)].map((m) => m[1]).sort();
}

describe('persona data', () => {
  it('lists exactly 10 principal-engineer personas', () => {
    expect(personas).toHaveLength(10);
  });

  it('has unique ids', () => {
    const ids = personas.map((p) => p.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('marks principal-backend-engineer as the single default persona', () => {
    const def = personas.filter((p) => p.path === 'default');
    expect(def).toHaveLength(1);
    expect(def[0].id).toBe('principal-backend-engineer');
    expect(def[0].id).toBe(defaultPersona);
  });

  it('agrees with the registry default_persona', () => {
    const m = registryToml.match(/^default_persona = "([^"]+)"/m);
    expect(m).not.toBeNull();
    expect(defaultPersona).toBe(m[1]);
  });

  it('ids match the [[persona]] blocks in pack/personas.toml', () => {
    const dataIds = personas.map((p) => p.id).sort();
    expect(dataIds).toEqual(registryIds());
  });

  it('every persona brings at least one skill', () => {
    for (const p of personas) {
      expect(Array.isArray(p.skills)).toBe(true);
      expect(p.skills.length).toBeGreaterThan(0);
    }
  });

  it('describes the lifecycle: materialize, execute, dematerialize, warm, age out', () => {
    expect(lifecycle.map((s) => s.name)).toEqual([
      'materialize',
      'execute',
      'dematerialize',
      'warm',
      'age out'
    ]);
  });

  it('describes the dispatch composition, with personas as the role dimension', () => {
    expect(composition.map((c) => c.id)).toEqual(['model-advisor', 'provider-forge', 'personas']);
    const role = composition.find((c) => c.dimension === 'Role');
    expect(role.id).toBe('personas');
  });
});

describe('roster matrix markup stays in sync with the data', () => {
  const html = readFileSync(join(siteRoot, 'roster', 'index.html'), 'utf8');

  for (const p of personas) {
    it(`renders ${p.id}: label, domain line, and data attribute`, () => {
      expect(html).toContain(`data-persona="${p.id}"`);
      expect(html).toContain(p.label);
      expect(html).toContain(p.best);
    });
  }

  it('marks principal-backend-engineer as the default cell', () => {
    expect(html).toContain('data-persona="principal-backend-engineer" data-path="default"');
  });
});
