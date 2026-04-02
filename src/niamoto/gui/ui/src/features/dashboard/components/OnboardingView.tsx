import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { ArrowRight, Globe, Info, Upload } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"

export function OnboardingView() {
  const { t } = useTranslation("common")
  const navigate = useNavigate()

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-4xl space-y-8 p-6 lg:p-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold">
            {t("pipeline.onboarding.title", "Commencer votre projet")}
          </h1>
          <p className="mt-2 text-muted-foreground">
            {t(
              "pipeline.onboarding.subtitle",
              "Commencez par importer vos données. Vous pourrez ensuite configurer les collections et publier votre portail.",
            )}
          </p>
        </div>

        <Card className="border-emerald-200/70 bg-gradient-to-br from-emerald-50 via-background to-background shadow-sm dark:border-emerald-900/40 dark:from-emerald-950/20">
          <CardContent className="flex flex-col gap-6 p-6 lg:flex-row lg:items-center lg:justify-between lg:p-8">
            <div className="space-y-4">
              <Badge
                variant="secondary"
                className="border border-emerald-200/80 bg-emerald-100 text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-100"
              >
                {t("pipeline.onboarding.required", "Étape requise")}
              </Badge>
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-600 text-white shadow-sm">
                    <Upload className="h-5 w-5" />
                  </div>
                  <h2 className="text-xl font-semibold">
                    {t("pipeline.onboarding.import_title", "Importer vos données")}
                  </h2>
                </div>
                <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                  {t(
                    "pipeline.onboarding.import_description",
                    "Ajoutez vos fichiers sources pour initialiser le projet: CSV, taxonomies, couches géographiques et autres tables de référence.",
                  )}
                </p>
              </div>
            </div>

            <Button
              size="lg"
              className="h-12 min-w-52 self-start bg-emerald-600 hover:bg-emerald-700"
              onClick={() => navigate("/sources/import")}
            >
              <Upload className="mr-2 h-4 w-4" />
              {t("pipeline.onboarding.open_import", "Ouvrir l’import")}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </CardContent>
        </Card>

        <div className="grid gap-4 lg:grid-cols-[1.2fr,0.8fr]">
          <Card className="border-muted/60 shadow-sm">
            <CardContent className="space-y-4 p-6">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-sky-100 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">
                  <Globe className="h-5 w-5" />
                </div>
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">
                      {t("pipeline.onboarding.site_title", "Préparer le site")}
                    </h3>
                    <Badge variant="outline">
                      {t("pipeline.onboarding.optional", "Optionnel")}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {t(
                      "pipeline.onboarding.site_description",
                      "Vous pouvez déjà préparer les pages, la navigation et la structure du portail pendant que les données arrivent.",
                    )}
                  </p>
                </div>
              </div>

              <Button
                variant="outline"
                className="w-full justify-between sm:w-auto"
                onClick={() => navigate("/site")}
              >
                {t("pipeline.onboarding.open_site", "Ouvrir le site builder")}
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </CardContent>
          </Card>

          <Card className="border-dashed border-muted-foreground/30 bg-muted/20 shadow-none">
            <CardContent className="space-y-3 p-6">
              <div className="flex items-start gap-3">
                <Info className="mt-0.5 h-4 w-4 text-muted-foreground" />
                <div className="space-y-2">
                  <h3 className="font-medium">
                    {t("pipeline.onboarding.unlock_title", "Ce qui viendra ensuite")}
                  </h3>
                  <p className="text-sm leading-6 text-muted-foreground">
                    {t(
                      "pipeline.onboarding.unlock_description",
                      "Les collections et la publication seront disponibles après l’import des premières données.",
                    )}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
