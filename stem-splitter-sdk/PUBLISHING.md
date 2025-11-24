# Publishing Guide - npm Package

## Prerequisites

1. **npm account**: Create one at https://www.npmjs.com/signup
2. **Login**: `npm login`
3. **Package name**: Check if `stem-splitter-api` is available

## Pre-Publishing Checklist

- [x] Package name is unique
- [x] Version number is correct (semantic versioning)
- [x] All dependencies are listed
- [x] README.md is complete
- [x] LICENSE file exists
- [x] TypeScript builds successfully
- [x] No sensitive data in package

## Build Steps

```bash
cd stem-splitter-sdk

# Install dependencies
npm install

# Build TypeScript
npm run build

# Verify build output
ls dist/
# Should see: index.js and index.d.ts
```

## Publishing Steps

### 1. Update Version (if needed)

```bash
# Patch version (1.0.0 -> 1.0.1)
npm version patch

# Minor version (1.0.0 -> 1.1.0)
npm version minor

# Major version (1.0.0 -> 2.0.0)
npm version major
```

### 2. Verify Package Contents

```bash
# Check what will be published
npm pack --dry-run

# Or create tarball to inspect
npm pack
tar -tzf stem-splitter-api-1.0.0.tgz
```

### 3. Publish to npm

```bash
# Dry run first (recommended)
npm publish --dry-run

# Publish to npm
npm publish

# Or publish with public access (if scoped package)
npm publish --access public
```

### 4. Verify Publication

```bash
# Check package on npm
npm view stem-splitter-api

# Test installation
npm install stem-splitter-api
```

## Post-Publishing

1. **Update documentation** with npm package link
2. **Create GitHub release** (if using GitHub)
3. **Announce** on social media/forums
4. **Monitor** for issues and feedback

## Updating the Package

```bash
# Make changes, then:
npm version patch  # or minor/major
npm run build
npm publish
```

## Troubleshooting

### Error: Package name already taken
- Choose a different name in `package.json`
- Or use scoped package: `@your-username/stem-splitter-api`

### Error: You must verify your email
- Check email and verify npm account

### Error: Missing files
- Check `.npmignore` file
- Verify `files` array in `package.json`

### Error: TypeScript errors
- Run `npm run build` to see errors
- Fix TypeScript issues before publishing

## Package Information

- **Name**: `stem-splitter-api`
- **Version**: `1.0.0`
- **License**: MIT
- **Node**: >=16.0.0
- **TypeScript**: Yes (types included)

## Files Included in Package

- `dist/index.js` - Compiled JavaScript
- `dist/index.d.ts` - TypeScript definitions
- `README.md` - Documentation
- `LICENSE` - MIT License

## Files Excluded

- `src/` - Source files (not needed)
- `tsconfig.json` - Build config
- `node_modules/` - Dependencies
- `.git/` - Git files

