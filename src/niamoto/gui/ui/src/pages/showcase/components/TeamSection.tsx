import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Mail,
  Github,
  Globe,
  BookOpen,
  Sparkles,
  Wand2,
  Bug,
  Hammer,
  HandHeart
} from 'lucide-react'
import niamotoLogo from '@/assets/niamoto_logo.png'

const coreTeam = [
  {
    name: 'Philippe Birnbaum',
    nickname: 'La Source',
    role: 'CIRAD - UMR AMAP',
    description: 'Le visionnaire qui a tout déclenché',
    icon: Sparkles,
    photo: '/team/philippe.png',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-600/10'
  },
  {
    name: 'Dimitri Justeau-Allaire',
    nickname: 'Le Sorcier',
    role: 'IRD - UMR AMAP',
    description: 'Le magicien des algorithmes et des données spatiales',
    icon: Wand2,
    photo: '/team/dimitri.jpeg',
    color: 'text-purple-600',
    bgColor: 'bg-purple-600/10'
  },
  {
    name: 'Gilles Dauby',
    nickname: 'Le Cobaye',
    role: 'IRD - UMR AMAP',
    description: 'Le testeur intrépide qui fait marcher tout ça',
    icon: Bug,
    photo: '/team/gilles.png',
    color: 'text-green-600',
    bgColor: 'bg-green-600/10'
  },
  {
    name: 'Julien Barbe',
    nickname: 'Le Bourreau',
    role: 'Indépendant',
    description: 'Le codeur qui transforme les rêves en réalité',
    icon: Hammer,
    photo: '/team/julien.png',
    color: 'text-red-600',
    bgColor: 'bg-red-600/10'
  }
]

const links = [
  {
    name: 'GitHub',
    icon: Github,
    url: 'https://github.com/niamoto/niamoto',
    description: 'Code source et contributions'
  },
  {
    name: 'Documentation',
    icon: BookOpen,
    url: 'https://niamoto.readthedocs.io/',
    description: 'Guides et tutoriels'
  },
  {
    name: 'Contact',
    icon: Mail,
    url: 'mailto:julien.barbe@me.com',
    description: 'Nous contacter'
  }
]

const partners = [
  {
    name: 'Province Nord',
    logo: '/partners/pn_100.png',
    url: 'https://www.province-nord.nc/',
    description: 'Partenaire institutionnel et financier'
  },
  {
    name: 'Province Sud',
    logo: '/partners/ps_100.png',
    url: 'https://www.province-sud.nc/',
    description: 'Partenaire institutionnel'
  },
  {
    name: 'Endemia',
    logo: '/partners/endemia_100.png',
    url: 'https://endemia.nc/',
    description: 'Plateforme collaborative sur la biodiversité'
  },
  {
    name: 'UMR AMAP',
    logo: '/partners/amap_100.png',
    url: 'https://amap.cirad.fr/',
    description: 'Unité Mixte de Recherche botAnique et Modélisation de l\'Architecture des Plantes'
  },
  {
    name: 'Herbarium',
    logo: '/partners/herbarium_100.png',
    url: 'http://publish.plantnet-project.org/project/nou',
    description: 'Herbier de Nouvelle-Calédonie'
  },
  {
    name: 'IAC',
    logo: '/partners/iac_100.png',
    url: 'https://iac.nc/',
    description: 'Institut Agronomique néo-Calédonien'
  },
  {
    name: 'IRD',
    logo: '/partners/ird_100.png',
    url: 'https://nouvelle-caledonie.ird.fr/',
    description: 'Institut de Recherche pour le Développement'
  },
  {
    name: 'Cirad',
    logo: '/partners/cirad_100.png',
    url: 'https://cirad.fr/',
    description: 'Centre de coopération internationale en recherche agronomique'
  },
  {
    name: 'OFB',
    logo: '/partners/ofb_100.png',
    url: 'https://www.ofb.gouv.fr/',
    description: 'Office Français de la Biodiversité'
  }
]

export function TeamSection() {
  return (
    <div className="w-full max-w-6xl mx-auto space-y-12 py-12">
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-3 mb-4">
          <img src={niamotoLogo} alt="Niamoto" className="w-14 h-14 object-contain" />
          <h2 className="text-4xl font-bold">Niamoteam</h2>
          <img src={niamotoLogo} alt="Niamoto" className="w-14 h-14 object-contain" />
        </div>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Projet collaboratif open-source pour la conservation de la biodiversité
        </p>
      </div>

      {/* Core Team - The Dream Team */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {coreTeam.map((member) => {
          const Icon = member.icon
          return (
            <Card key={member.name} className="border-2 hover:shadow-xl transition-all hover:scale-105">
              <CardHeader className="text-center">
                {/* Photo placeholder with icon */}
                <div className="mb-6 mx-auto relative">
                  <div className={`w-32 h-32 rounded-full ${member.bgColor} flex items-center justify-center overflow-hidden border-4 border-background shadow-lg`}>
                    {/* Photo will be shown when added, icon as fallback */}
                    <img
                      src={member.photo}
                      alt={member.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        // Fallback to icon if image not found
                        e.currentTarget.style.display = 'none'
                        const iconContainer = e.currentTarget.nextElementSibling as HTMLElement
                        if (iconContainer) iconContainer.style.display = 'flex'
                      }}
                    />
                    <div className="w-full h-full hidden items-center justify-center">
                      <Icon className={`w-16 h-16 ${member.color}`} />
                    </div>
                  </div>
                  {/* Badge with nickname and icon */}
                  <Badge
                    className={`absolute -bottom-3 left-1/2 -translate-x-1/2 bg-white dark:bg-gray-900 ${member.color} border-2 border-background shadow-lg font-bold px-3 py-1 flex items-center gap-1.5`}
                  >
                    <Icon className={`w-4 h-4 ${member.color}`} />
                    {member.nickname}
                  </Badge>
                </div>

                <CardTitle className="text-xl mt-4">{member.name}</CardTitle>
                <CardDescription className="text-sm font-medium">{member.role}</CardDescription>
              </CardHeader>
              <CardContent className="text-center">
                <p className="text-sm text-muted-foreground italic">
                  {member.description}
                </p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Partners & Funders */}
      <Card className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-950/20 dark:to-blue-900/20 border-blue-200 dark:border-blue-800">
        <CardHeader>
          <div className="flex items-center gap-3 mb-2">
            <HandHeart className="w-6 h-6 text-blue-600" />
            <CardTitle>Partenaires & Financeurs</CardTitle>
          </div>
          <CardDescription className="text-base">
            Le développement de Niamoto s'inscrit dans le cadre du projet de recherche
            <strong className="text-foreground"> "Partenariat pour l'Analyse des DynaMIques de REforestation et de la résilience forestière (ADMIRE)"</strong>,
            établi entre la Province Nord, l'IAC et le Cirad. Ce projet vise à développer des outils informatiques
            pour l'aide à la décision dans la gestion des espaces naturels de la Province Nord de la Nouvelle-Calédonie.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 md:grid-cols-5 gap-6 items-center justify-items-center">
            {partners.map((partner) => (
              <a
                key={partner.name}
                href={partner.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex flex-col items-center gap-3 group"
              >
                <div className="w-20 h-20 bg-white dark:bg-gray-800 rounded-lg p-2 shadow-md group-hover:shadow-xl transition-all group-hover:scale-105 flex items-center justify-center">
                  <img
                    src={partner.logo}
                    alt={partner.name}
                    className="w-full h-full object-contain"
                    title={partner.description}
                  />
                </div>
                <p className="text-xs text-center text-muted-foreground font-medium group-hover:text-foreground transition-colors">
                  {partner.name}
                </p>
              </a>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Links & Contact */}
      <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
        <CardHeader>
          <CardTitle>Rejoignez-nous</CardTitle>
          <CardDescription>
            Contribuez au projet ou contactez-nous pour en savoir plus
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {links.map((link) => {
              const Icon = link.icon
              return (
                <Button
                  key={link.name}
                  variant="outline"
                  className="h-auto flex-col items-start p-4 hover:bg-primary/10"
                  asChild
                >
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full"
                  >
                    <div className="flex items-center gap-2 mb-2 w-full">
                      <Icon className="w-5 h-5" />
                      <span className="font-semibold">{link.name}</span>
                    </div>
                    <p className="text-xs text-muted-foreground text-left">
                      {link.description}
                    </p>
                  </a>
                </Button>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Open Source Notice */}
      <Card className="text-center border-dashed">
        <CardContent className="pt-6">
          <div className="flex items-center justify-center gap-2 mb-3">
            <Globe className="w-5 h-5 text-green-600" />
            <Badge variant="outline" className="text-green-600 border-green-600">
              Open Source
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground max-w-2xl mx-auto">
            Niamoto est un projet open-source sous licence GPL-3.0. Toutes les contributions sont les bienvenues !
            <br />
            <span className="text-xs opacity-75">
              Développé avec passion pour la conservation de la biodiversité mondiale
            </span>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
