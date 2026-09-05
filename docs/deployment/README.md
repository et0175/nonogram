# Deployment Directory

Complete deployment and infrastructure documentation for the Nonogram project.

## Subdirectories

### guides/
Step-by-step deployment procedures and configuration guides.

**Key Documents:**
- DEPLOYMENT_GUIDE.md - Complete production deployment walkthrough
- Infrastructure setup and configuration
- Environment variable configuration
- Health checks and monitoring setup

### infrastructure/
Cloud platform and infrastructure-specific documentation.

**Key Documents:**
- RAILWAY_DEPLOYMENT.md - Railway.app deployment setup
- RAILWAY_AGENT_GUIDE.md - Using Railway agents for CI/CD
- Docker configuration and container setup
- Database migration procedures

## Deployment Checklist

Before deploying to production:

- [ ] Review DEPLOYMENT_GUIDE.md
- [ ] Verify environment variables are configured
- [ ] Run complete test suite locally
- [ ] Build Docker image and test
- [ ] Verify database migrations
- [ ] Check health endpoints
- [ ] Set up monitoring and logging
- [ ] Prepare rollback plan
- [ ] Document any configuration changes
- [ ] Update deployment status in reports/

## Quick Start

1. **Local Setup:**
   - Follow ../development/setup/ instructions
   - Install all dependencies

2. **Staging Deployment:**
   - Follow guides/DEPLOYMENT_GUIDE.md
   - Use staging environment variables

3. **Production Deployment:**
   - Complete staging validation
   - Follow infrastructure-specific guides (e.g., RAILWAY_DEPLOYMENT.md)
   - Monitor deployment logs

## Platform-Specific Guides

- **Railway.app** → infrastructure/RAILWAY_DEPLOYMENT.md
- **Docker** → Dockerfile in project root + docker-specific docs
- **Local** → deployment/guides/DEPLOYMENT_GUIDE.md

## Post-Deployment

- Monitor health endpoints
- Check application logs
- Verify all features working
- Run smoke tests
- Update deployment status in reports/deployment-reports/

## Troubleshooting

Common deployment issues and solutions:
- See ../development/troubleshooting/ for common problems
- Check deployment reports in ../reports/deployment-reports/
- Review application logs for errors

---
Last updated: 2026-09-05
