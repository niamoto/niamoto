import { useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { ArrowRight, Globe, Layers, Send, Upload } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"

export function OnboardingView() {
  const { t } = useTranslation("common")
  const navigate = useNavigate()

  const steps = [
    {
      number: 1,
      title: t("pipeline.onboarding.step1", "Import your data"),
      description: t(
        "pipeline.onboarding.step1_desc",
        "Fichiers CSV, taxonomie, shapefile",
      ),
      path: "/sources/import",
      icon: <Upload className="h-5 w-5" />,
    },
    {
      number: 2,
      title: t("pipeline.onboarding.step2", "Configure groups"),
      description: t(
        "pipeline.onboarding.step2_desc",
        "Choose widgets and statistics to compute",
      ),
      path: "/groups",
      icon: <Layers className="h-5 w-5" />,
    },
    {
      number: 3,
      title: t("pipeline.onboarding.step3", "Customize the site"),
      description: t(
        "pipeline.onboarding.step3_desc",
        "Pages, navigation, appearance",
      ),
      path: "/site",
      icon: <Globe className="h-5 w-5" />,
    },
    {
      number: 4,
      title: t("pipeline.onboarding.step4", "Publish"),
      description: t(
        "pipeline.onboarding.step4_desc",
        "Build and deploy the website",
      ),
      path: "/publish",
      icon: <Send className="h-5 w-5" />,
    },
  ]

  return (
    <div className="mx-auto max-w-2xl space-y-8 p-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">
          {t("pipeline.onboarding.title", "Welcome to Niamoto")}
        </h1>
        <p className="mt-2 text-muted-foreground">
          {t(
            "pipeline.onboarding.subtitle",
            "Follow these steps to set up your ecological data portal.",
          )}
        </p>
      </div>

      <div className="space-y-3">
        {steps.map((step) => (
          <Card
            key={step.number}
            className="cursor-pointer transition-colors hover:bg-accent/50"
            onClick={() => navigate(step.path)}
          >
            <CardContent className="flex items-center gap-4 p-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-bold text-muted-foreground">
                {step.number}
              </div>
              <div className="flex-1">
                <p className="font-medium">{step.title}</p>
                <p className="text-sm text-muted-foreground">
                  {step.description}
                </p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground">
                {step.icon}
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
