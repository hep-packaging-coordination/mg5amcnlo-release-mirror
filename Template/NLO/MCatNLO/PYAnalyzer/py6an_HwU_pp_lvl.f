c
c Example analysis for "p p > l v [QCD]" process.
c
c It features the HwU format for histogram booking and output.
c The details of how to process/manipulate the resulting .HwU file,
c in particular how to plot it using gnuplot, I refer the reader to this
c FAQ:
c
c      https://answers.launchpad.net/mg5amcnlo/+faq/2671
c
c It mostly relies on using the following madgraph5 module in standalone
c
c  <MG5_aMC_install_dir>/madgraph/various/histograms.py
c
c You can learn about how to run it and what options are available with
c
c  python <MG5_aMC_install_dir>/madgraph/various/histograms.py --help
c
C----------------------------------------------------------------------
      SUBROUTINE RCLOS()
C     DUMMY IF HBOOK IS USED
C----------------------------------------------------------------------
      END


C----------------------------------------------------------------------
      SUBROUTINE PYABEG
C     USER''S ROUTINE FOR INITIALIZATION
C----------------------------------------------------------------------
      use HwU_wgts_info_len
      implicit double precision(a-h, o-z)
      implicit integer(i-n)
      common/pydat2/kchg(500,4),pmas(500,4),parf(2000),vckm(4,4)
      include 'reweight0.inc'
      real * 8 bin,xmi,xms,pi
      PARAMETER (PI=3.14159265358979312D0)
c
c     The type suffix of the histogram title, with syntax 
c     |T@<type_name> is semantic in the HwU format. It allows for
c     various filtering when using the histogram.py module
c     (see comment at the beginning of this file).
c     It is in general a good idea to keep the same title for the
c     same observable (if they use the same range) and differentiate
c     them only using the type suffix.
c
      character*8 HwUtype(2)
      data HwUtype/'|T@NOCUT','|T@CUT  '/
      integer j,kk,l,jpr,i
      character*5 cc(2)
      data cc/'     ','Born '/
      integer nwgt,max_weight,nwgt_analysis
      common/cnwgt/nwgt
      common/c_analysis/nwgt_analysis
      character*(wgts_info_len) weights_info(max_weight_shower)
      common/cwgtsinfo/weights_info
c Initialize histograms
      call HwU_inithist(nwgt,weights_info)
c Set method for error estimation to '0', i.e., use Poisson statistics
c for the uncertainty estimate
      call set_error_estimation(0)
      nwgt_analysis=nwgt
      do i=1,1
        call HwU_book(l+1,'total rate   '//HwUtype(i),2,-2.d0,2.d0)
        call HwU_book(l+2,'lep rapidity '//HwUtype(i),40,-9d0,9d0)
        call HwU_book(l+3,'lep pt       '//HwUtype(i),100,0d0,200d0)
        call HwU_book(l+4,'et miss      '//HwUtype(i),100,0d0,200d0)
        call HwU_book(l+5,'trans. mass  '//HwUtype(i),100,0d0,200d0)
        call HwU_book(l+6,'w rapidity   '//HwUtype(i),40,-9d0,9d0)
        call HwU_book(l+7,'w pt         '//HwUtype(i),100,0d0,200d0)
        call HwU_book(l+8,'cphi[l,vl]   '//HwUtype(i),40,-1d0,1d0)
      enddo

      END

C----------------------------------------------------------------------
      SUBROUTINE PYAEND(IEVT)
C     USER''S ROUTINE FOR TERMINAL CALCULATIONS, HISTOGRAM OUTPUT, ETC
C----------------------------------------------------------------------
      REAL*8 XNORM
      INTEGER I,J,KK,l,nwgt_analysis
      integer NPL
      parameter(NPL=15000)
      common/c_analysis/nwgt_analysis
c Convert from nb to pb using xnorm. This assumes that event weights
c *average* to the total cross section, so no extra weight needed
      xnorm=1d0
c Collect accumulated results
      call finalize_histograms(ievt)
c Write the histograms to disk. 
      open (unit=99,file='MADatNLO.HwU',status='unknown')
      call HwU_output(99,xnorm)
      close (99)
      return
      END

C----------------------------------------------------------------------
      SUBROUTINE PYANAL
C     USER''S ROUTINE TO ANALYSE DATA FROM EVENT
C----------------------------------------------------------------------
      implicit double precision(a-h, o-z)
      implicit integer(i-n)
      include 'reweight0.inc'
      DOUBLE PRECISION HWVDOT,PSUM(4),PPV(5),PTW,YW,YE,PPL(5),PPLB(5),
     & PTE,PLL,PTLB,PLLB,var,mtr,etmiss,cphi
      INTEGER ICHSUM,ICHINI,IHEP,IV,IFV,IST,ID,IJ,ID1,JPR,IDENT,
     #  ILL,ILLB,IHRD
      integer pychge
      double precision p1(4),p2(4),pihep(4)
      external pydata
      common/pyjets/n,npad,k(4000,5),p(4000,5),v(4000,5)
      common/pydat1/mstu(200),paru(200),mstj(200),parj(200)
      common/pydat2/kchg(500,4),pmas(500,4),parf(2000),vckm(4,4)
      common/pydat3/mdcy(500,3),mdme(8000,2),brat(8000),kfdp(8000,5)
      common/pysubs/msel,mselpd,msub(500),kfin(2,-40:40),ckin(200)
      common/pypars/mstp(200),parp(200),msti(200),pari(200)
      LOGICAL DIDSOF,FOUNDL,FOUNDN,ISL,ISN
      REAL*8 PI,getrapidity
      PARAMETER (PI=3.14159265358979312D0)
      REAL*8 WWW0,TINY,SIGNL,SIGNN
      INTEGER KK,I,L,IL,IN
      DATA TINY/.1D-5/
      integer nwgt_analysis,max_weight
      common/c_analysis/nwgt_analysis
      integer maxRWGT
      parameter (maxRWGT=100)
      double precision wgtxsecRWGT(maxRWGT)
      parameter (max_weight=maxscales*maxscales+maxpdfs+maxRWGT+1)
      double precision ww(max_weight),www(max_weight)
      common/cww/ww
      DOUBLE PRECISION EVWEIGHT
      COMMON/CEVWEIGHT/EVWEIGHT
      INTEGER IFAIL
      COMMON/CIFAIL/IFAIL
c
      IF(IFAIL.EQ.1)RETURN
      IF (WW(1).EQ.0D0) THEN
         WRITE(*,*)'WW(1) = 0. Stopping'
         STOP
      ENDIF
C CHOOSE IDENT = 11 FOR E - NU_E
C        IDENT = 13 FOR MU - NU_MU
C        IDENT = 15 FOR TAU - NU_TAU
      IDENT=11
C INCOMING PARTONS MAY TRAVEL IN THE SAME DIRECTION: IT''S A POWER-SUPPRESSED
C EFFECT, SO THROW THE EVENT AWAY
      IF(SIGN(1.D0,P(3,3)).EQ.SIGN(1.D0,P(4,3)))THEN
         WRITE(*,*)'WARNING 111 IN PYANAL'
         GOTO 999
      ENDIF
      DO I=1,nwgt_analysis
         WWW(I)=EVWEIGHT*ww(i)/ww(1)
      ENDDO
      DO I=1,4
         P1(I)=P(1,I)
         P2(I)=P(2,I)
      ENDDO
      CALL VVSUM(4,P1,P2,PSUM)
      CALL VSCA(4,-1D0,PSUM,PSUM)
      ICHSUM=0
      KF1=K(1,2)
      KF2=K(2,2)
      ICHINI=PYCHGE(KF1)+PYCHGE(KF2)
C
      DO 100 IHEP=1,N
        DO J=1,4
          PIHEP(J)=P(IHEP,J)
        ENDDO
        IST =K(IHEP,1)
        ID1 =K(IHEP,2)
        IORI=K(IHEP,3)
        IF (IST.LE.10) THEN
          CALL VVSUM(4,PIHEP,PSUM,PSUM)
          ICHSUM=ICHSUM+PYCHGE(ID1)
        ENDIF
        ISL=ABS(ID1).EQ.IDENT
        ISN=ABS(ID1).EQ.IDENT+1
        IF(IORI.LE.10..AND.ISL)THEN
            IL=IHEP
            FOUNDL=.TRUE.
            SIGNL=SIGN(1D0,DBLE(ID1))
         ENDIF
         IF(IORI.LE.10.AND.ISN)THEN
            IN=IHEP
            FOUNDN=.TRUE.
            SIGNN=SIGN(1D0,DBLE(ID1))
         ENDIF
  100 CONTINUE
      IF(.NOT.FOUNDL.OR..NOT.FOUNDN)THEN
         WRITE(*,*)'NO LEPTONS FOUND.'
         WRITE(*,*)'CURRENTLY THIS ANALYSIS LOOKS FOR'
         IF(IDENT.EQ.11)WRITE(*,*)'E - NU_E'
         IF(IDENT.EQ.13)WRITE(*,*)'MU - NU_MU'
         IF(IDENT.EQ.15)WRITE(*,*)'TAU - NU_TAU'
         WRITE(*,*)'IF THIS IS NOT MEANT,'
         WRITE(*,*)'PLEASE CHANGE THE VALUE OF IDENT IN THIS FILE.'
         STOP
      ENDIF
      IF(SIGNN.EQ.SIGNL)THEN
         WRITE(*,*)'TWO SAME SIGN LEPTONS!'
         WRITE(*,*)IL,IN,SIGNL,SIGNN
         STOP
      ENDIF
C CHECK MOMENTUM AND CHARGE CONSERVATION
      IF (VDOT(3,PSUM,PSUM).GT.1.E-4*P(1,4)**2) THEN
         WRITE(*,*)'WARNING 112 IN PYANAL'
         GOTO 999
      ENDIF
      IF (ICHSUM.NE.ICHINI) THEN
         WRITE(*,*)'WARNING 113 IN PYANAL'
         GOTO 999
      ENDIF
      DO IJ=1,5
        PPL(IJ) =P(IN, IJ)
        PPLB(IJ)=P(IL,IJ)
        PPV(IJ)=PPL(IJ)+PPLB(IJ)
      ENDDO
      ye     = getrapidity(pplb(4), pplb(3))
      yw     = getrapidity(ppv(4), ppv(3))
      pte    = dsqrt(pplb(1)**2 + pplb(2)**2)
      ptw    = dsqrt(ppv(1)**2+ppv(2)**2)
      etmiss = dsqrt(ppl(1)**2 + ppl(2)**2)
      mtr    = dsqrt(2d0*pte*etmiss-2d0*ppl(1)*pplb(1)-2d0*ppl(2)*pplb(2))
      cphi   = (ppl(1)*pplb(1)+ppl(2)*pplb(2))/pte/etmiss
      var    = 1.d0
      do i=1,1
         l=(i-1)*8
         call HwU_fill(l+1,var,WWW)
         call HwU_fill(l+2,ye,WWW)
         call HwU_fill(l+3,pte,WWW)
         call HwU_fill(l+4,etmiss,WWW)
         call HwU_fill(l+5,mtr,WWW)
         call HwU_fill(l+6,yw,WWW)
         call HwU_fill(l+7,ptw,WWW)
         call HwU_fill(l+8,cphi,WWW)
      enddo
      call HwU_add_points
 999  END
      

C-----------------------------------------------------------------------
      SUBROUTINE VVSUM(N,P,Q,R)
C-----------------------------------------------------------------------
C    VECTOR SUM
C-----------------------------------------------------------------------
      IMPLICIT NONE
      INTEGER N,I
      DOUBLE PRECISION P(N),Q(N),R(N)
      DO 10 I=1,N
   10 R(I)=P(I)+Q(I)
      END



C-----------------------------------------------------------------------
      SUBROUTINE VSCA(N,C,P,Q)
C-----------------------------------------------------------------------
C     VECTOR TIMES SCALAR
C-----------------------------------------------------------------------
      IMPLICIT NONE
      INTEGER N,I
      DOUBLE PRECISION C,P(N),Q(N)
      DO 10 I=1,N
   10 Q(I)=C*P(I)
      END



C-----------------------------------------------------------------------
      FUNCTION VDOT(N,P,Q)
C-----------------------------------------------------------------------
C     VECTOR DOT PRODUCT
C-----------------------------------------------------------------------
      IMPLICIT NONE
      INTEGER N,I
      DOUBLE PRECISION VDOT,PQ,P(N),Q(N)
      PQ=0.
      DO 10 I=1,N
   10 PQ=PQ+P(I)*Q(I)
      VDOT=PQ
      END

      function getrapidity(en,pl)
      implicit none
      real*8 getrapidity,en,pl,tiny,xplus,xminus,y
      parameter (tiny=1.d-8)
      xplus=en+pl
      xminus=en-pl
      if(xplus.gt.tiny.and.xminus.gt.tiny)then
         if( (xplus/xminus).gt.tiny.and.(xminus/xplus).gt.tiny)then
            y=0.5d0*log( xplus/xminus  )
         else
            y=sign(1.d0,pl)*1.d8
         endif
      else 
         y=sign(1.d0,pl)*1.d8
      endif
      getrapidity=y
      return
      end
