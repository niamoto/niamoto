# Publish

Publish is the final desktop stage. Use it to build the generated site, inspect
the result, choose a deployment target, and follow the deployment status to the
end.

## What this stage is for

Publish is where you:

- generate the site from the current project state
- check the built preview
- pick a deployment target
- review logs and the final result

This stage comes after [site.md](site.md).

## 1. Build and inspect the generated site

Before deploying, generate the site and check the built preview inside the app.

![Publish preview](../assets/screenshots/desktop/25.publish-generation-preview.png)

This is the best checkpoint for deciding whether you should publish now or go
back to Site or Collections for another adjustment.

## 2. Choose a deployment target

When the generated preview looks right, select the destination that should
receive the site.

![Deployment target picker](../assets/screenshots/desktop/26.deploy-provider-picker.png)

The current desktop product exposes these publish destinations:

- Cloudflare Workers
- GitHub Pages
- Netlify
- Vercel
- Render
- SSH / rsync

## 3. Fill in provider settings

Each destination has its own configuration surface. For example, GitHub Pages
asks for the repository-oriented settings needed to publish the built output.

![GitHub Pages configuration](../assets/screenshots/desktop/27.deploy-github-pages-config.png)

## 4. Review logs and final status

Publish keeps the build and deployment lifecycle visible while the job runs.

![Deployment build log](../assets/screenshots/desktop/28.deploy-build-log.png)

When the deployment finishes, the success state confirms that the generated
portal was uploaded correctly.

![Deployment success](../assets/screenshots/desktop/29.deploy-success.png)

## Behind the UI

If you work directly with project files, the build side of this stage is mostly
driven by `config/export.yml`. In the desktop app, deployment settings are
managed from the UI, and credentials are stored through the OS keyring. For CLI
automation, `config/deploy.yml` can still provide deployment defaults.

## Related

- [site.md](site.md)
- [preview.md](preview.md)
- [../03-cli-automation/README.md](../03-cli-automation/README.md)
- [../06-reference/api-export-guide.md](../06-reference/api-export-guide.md)
