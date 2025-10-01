import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Mail,
  Github,
  Globe,
  Heart,
  BookOpen,
  Sparkles,
  Wand2,
  Bug,
  Hammer
} from 'lucide-react'

const coreTeam = [
  {
    name: 'Philippe Birnbaum',
    nickname: 'La Source',
    role: 'IRD - UMR AMAP',
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

export function TeamSection() {
  return (
    <div className="w-full max-w-6xl mx-auto space-y-12 py-12">
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Heart className="w-8 h-8 text-red-500 fill-red-500" />
          <h2 className="text-4xl font-bold">Équipe & Communauté</h2>
          <Heart className="w-8 h-8 text-red-500 fill-red-500" />
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
