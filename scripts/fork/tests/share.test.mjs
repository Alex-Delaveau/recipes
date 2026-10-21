import {test} from 'node:test'
import assert from 'node:assert/strict'
import {extractSharedUrl} from '../../../vue3/src/fork/share.ts'

test('url field wins', () => assert.equal(extractSharedUrl('https://a.fr/r', 'x https://b.fr', ''), 'https://a.fr/r'))
test('url buried in text', () => assert.equal(extractSharedUrl('', 'Recette de tarte https://www.marmiton.org/recettes/tarte-123.aspx', 'Tarte'), 'https://www.marmiton.org/recettes/tarte-123.aspx'))
test('url in title only', () => assert.equal(extractSharedUrl(null, 'Regarde ça', 'Tarte https://x.fr/t'), 'https://x.fr/t'))
test('trailing punctuation dropped', () => assert.equal(extractSharedUrl(undefined, 'Super (https://x.fr/t).', undefined), 'https://x.fr/t'))
test('bogus url field is skipped', () => assert.equal(extractSharedUrl('Recette', 'https://x.fr/t', ''), 'https://x.fr/t'))
test('nothing', () => assert.equal(extractSharedUrl('', 'pas de lien', null), null))
test('query param arrays', () => assert.equal(extractSharedUrl(['', 'https://x.fr/a']), 'https://x.fr/a'))
