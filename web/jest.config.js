const nextJest = require('next/jest')

const createJestConfig = nextJest({
  // Points to Next.js app to load next.config.js and .env files
  dir: './',
})

/** @type {import('jest').Config} */
const customJestConfig = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
  collectCoverageFrom: [
    'components/**/*.{ts,tsx}',
    'lib/**/*.{ts,tsx}',
    '!**/*.d.ts',
    '!**/index.ts',
  ],
  // Ensure transformIgnorePatterns doesn't exclude ESM packages we need
  transformIgnorePatterns: [
    '/node_modules/(?!(lucide-react)/)',
  ],
  // Do not treat test helper files as test suites
  testPathIgnorePatterns: [
    '<rootDir>/__tests__/test-utils\\.tsx$',
  ],
}

module.exports = createJestConfig(customJestConfig)
