// Do NOT change. Changes will be lost next time file is generated

#define R__DICTIONARY_FILENAME dItmpdIbdIjunodOihepdOacdOcndIel9_amd64_gcc11dIReleasedIJ25dO7dO1dItaoswdIbuilddIDataModeldICalibEventdIsrcdICdCalibEvtDict
#define R__NO_DEPRECATION

/*******************************************************************/
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define G__DICTIONARY
#include "ROOT/RConfig.hxx"
#include "TClass.h"
#include "TDictAttributeMap.h"
#include "TInterpreter.h"
#include "TROOT.h"
#include "TBuffer.h"
#include "TMemberInspector.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "TError.h"

#ifndef G__ROOT
#define G__ROOT
#endif

#include "RtypesImp.h"
#include "TIsAProxy.h"
#include "TFileMergeInfo.h"
#include <algorithm>
#include "TCollectionProxyInfo.h"
/*******************************************************************/

#include "TDataMember.h"

// Header files passed as explicit arguments
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/Event/CdCalibEvt.h"

// Header files passed via #pragma extra_include

// The generated code does not explicitly qualify STL entities
namespace std {} using namespace std;

namespace ROOT {
   static void *new_TaocLcLCdCalibEvt(void *p = nullptr);
   static void *newArray_TaocLcLCdCalibEvt(Long_t size, void *p);
   static void delete_TaocLcLCdCalibEvt(void *p);
   static void deleteArray_TaocLcLCdCalibEvt(void *p);
   static void destruct_TaocLcLCdCalibEvt(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const ::Tao::CdCalibEvt*)
   {
      ::Tao::CdCalibEvt *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TInstrumentedIsAProxy< ::Tao::CdCalibEvt >(nullptr);
      static ::ROOT::TGenericClassInfo 
         instance("Tao::CdCalibEvt", ::Tao::CdCalibEvt::Class_Version(), "Event/CdCalibEvt.h", 9,
                  typeid(::Tao::CdCalibEvt), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &::Tao::CdCalibEvt::Dictionary, isa_proxy, 4,
                  sizeof(::Tao::CdCalibEvt) );
      instance.SetNew(&new_TaocLcLCdCalibEvt);
      instance.SetNewArray(&newArray_TaocLcLCdCalibEvt);
      instance.SetDelete(&delete_TaocLcLCdCalibEvt);
      instance.SetDeleteArray(&deleteArray_TaocLcLCdCalibEvt);
      instance.SetDestructor(&destruct_TaocLcLCdCalibEvt);
      return &instance;
   }
   TGenericClassInfo *GenerateInitInstance(const ::Tao::CdCalibEvt*)
   {
      return GenerateInitInstanceLocal(static_cast<::Tao::CdCalibEvt*>(nullptr));
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const ::Tao::CdCalibEvt*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));
} // end of namespace ROOT

namespace Tao {
//______________________________________________________________________________
atomic_TClass_ptr CdCalibEvt::fgIsA(nullptr);  // static to hold class pointer

//______________________________________________________________________________
const char *CdCalibEvt::Class_Name()
{
   return "Tao::CdCalibEvt";
}

//______________________________________________________________________________
const char *CdCalibEvt::ImplFileName()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdCalibEvt*)nullptr)->GetImplFileName();
}

//______________________________________________________________________________
int CdCalibEvt::ImplFileLine()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdCalibEvt*)nullptr)->GetImplFileLine();
}

//______________________________________________________________________________
TClass *CdCalibEvt::Dictionary()
{
   fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdCalibEvt*)nullptr)->GetClass();
   return fgIsA;
}

//______________________________________________________________________________
TClass *CdCalibEvt::Class()
{
   if (!fgIsA.load()) { R__LOCKGUARD(gInterpreterMutex); fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdCalibEvt*)nullptr)->GetClass(); }
   return fgIsA;
}

} // namespace Tao
namespace Tao {
//______________________________________________________________________________
void CdCalibEvt::Streamer(TBuffer &R__b)
{
   // Stream an object of class Tao::CdCalibEvt.

   if (R__b.IsReading()) {
      R__b.ReadClassBuffer(Tao::CdCalibEvt::Class(),this);
   } else {
      R__b.WriteClassBuffer(Tao::CdCalibEvt::Class(),this);
   }
}

} // namespace Tao
namespace ROOT {
   // Wrappers around operator new
   static void *new_TaocLcLCdCalibEvt(void *p) {
      return  p ? new(p) ::Tao::CdCalibEvt : new ::Tao::CdCalibEvt;
   }
   static void *newArray_TaocLcLCdCalibEvt(Long_t nElements, void *p) {
      return p ? new(p) ::Tao::CdCalibEvt[nElements] : new ::Tao::CdCalibEvt[nElements];
   }
   // Wrapper around operator delete
   static void delete_TaocLcLCdCalibEvt(void *p) {
      delete (static_cast<::Tao::CdCalibEvt*>(p));
   }
   static void deleteArray_TaocLcLCdCalibEvt(void *p) {
      delete [] (static_cast<::Tao::CdCalibEvt*>(p));
   }
   static void destruct_TaocLcLCdCalibEvt(void *p) {
      typedef ::Tao::CdCalibEvt current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class ::Tao::CdCalibEvt

namespace ROOT {
   static TClass *vectorlETaocLcLCdCalibChannelgR_Dictionary();
   static void vectorlETaocLcLCdCalibChannelgR_TClassManip(TClass*);
   static void *new_vectorlETaocLcLCdCalibChannelgR(void *p = nullptr);
   static void *newArray_vectorlETaocLcLCdCalibChannelgR(Long_t size, void *p);
   static void delete_vectorlETaocLcLCdCalibChannelgR(void *p);
   static void deleteArray_vectorlETaocLcLCdCalibChannelgR(void *p);
   static void destruct_vectorlETaocLcLCdCalibChannelgR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<Tao::CdCalibChannel>*)
   {
      vector<Tao::CdCalibChannel> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<Tao::CdCalibChannel>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<Tao::CdCalibChannel>", -2, "vector", 389,
                  typeid(vector<Tao::CdCalibChannel>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlETaocLcLCdCalibChannelgR_Dictionary, isa_proxy, 0,
                  sizeof(vector<Tao::CdCalibChannel>) );
      instance.SetNew(&new_vectorlETaocLcLCdCalibChannelgR);
      instance.SetNewArray(&newArray_vectorlETaocLcLCdCalibChannelgR);
      instance.SetDelete(&delete_vectorlETaocLcLCdCalibChannelgR);
      instance.SetDeleteArray(&deleteArray_vectorlETaocLcLCdCalibChannelgR);
      instance.SetDestructor(&destruct_vectorlETaocLcLCdCalibChannelgR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<Tao::CdCalibChannel> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<Tao::CdCalibChannel>","std::vector<Tao::CdCalibChannel, std::allocator<Tao::CdCalibChannel> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<Tao::CdCalibChannel>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlETaocLcLCdCalibChannelgR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<Tao::CdCalibChannel>*>(nullptr))->GetClass();
      vectorlETaocLcLCdCalibChannelgR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlETaocLcLCdCalibChannelgR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlETaocLcLCdCalibChannelgR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::CdCalibChannel> : new vector<Tao::CdCalibChannel>;
   }
   static void *newArray_vectorlETaocLcLCdCalibChannelgR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::CdCalibChannel>[nElements] : new vector<Tao::CdCalibChannel>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlETaocLcLCdCalibChannelgR(void *p) {
      delete (static_cast<vector<Tao::CdCalibChannel>*>(p));
   }
   static void deleteArray_vectorlETaocLcLCdCalibChannelgR(void *p) {
      delete [] (static_cast<vector<Tao::CdCalibChannel>*>(p));
   }
   static void destruct_vectorlETaocLcLCdCalibChannelgR(void *p) {
      typedef vector<Tao::CdCalibChannel> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<Tao::CdCalibChannel>

namespace {
  void TriggerDictionaryInitialization_CdCalibEvtDict_Impl() {
    static const char* headers[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/Event/CdCalibEvt.h",
nullptr
    };
    static const char* includePaths[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Python/3.11.10/include/python3.11",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Boost/1.85.0",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/log4cpp/1.1.3/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/ROOT/6.30.08/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J24.2.0/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Geant4/10.04.p02.juno/include/geant4",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/HepMC/2.06.11/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/genie/3.04.02/include/GENIE",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/frontier/2.10.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-c/6.1.9/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-cpp/1.1.12/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libyaml/0.2.4/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime/core/session",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/nuwro/21.09.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/CalibEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.4.0/ExternalLibs/ROOT/6.30.08/include/",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/CalibEvent/",
nullptr
    };
    static const char* fwdDeclCode = R"DICTFWDDCLS(
#line 1 "CdCalibEvtDict dictionary forward declarations' payload"
#pragma clang diagnostic ignored "-Wkeyword-compat"
#pragma clang diagnostic ignored "-Wignored-attributes"
#pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
extern int __Cling_AutoLoading_Map;
namespace Tao{class __attribute__((annotate("$clingAutoload$/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/Event/CdCalibEvt.h")))  CdCalibEvt;}
)DICTFWDDCLS";
    static const char* payloadCode = R"DICTPAYLOAD(
#line 1 "CdCalibEvtDict dictionary payload"


#define _BACKWARD_BACKWARD_WARNING_H
// Inline headers
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/CalibEvent/Event/CdCalibEvt.h"

#undef  _BACKWARD_BACKWARD_WARNING_H
)DICTPAYLOAD";
    static const char* classesHeaders[] = {
"Tao::CdCalibEvt", payloadCode, "@",
nullptr
};
    static bool isInitialized = false;
    if (!isInitialized) {
      TROOT::RegisterModule("CdCalibEvtDict",
        headers, includePaths, payloadCode, fwdDeclCode,
        TriggerDictionaryInitialization_CdCalibEvtDict_Impl, {}, classesHeaders, /*hasCxxModule*/false);
      isInitialized = true;
    }
  }
  static struct DictInit {
    DictInit() {
      TriggerDictionaryInitialization_CdCalibEvtDict_Impl();
    }
  } __TheDictionaryInitializer;
}
void TriggerDictionaryInitialization_CdCalibEvtDict() {
  TriggerDictionaryInitialization_CdCalibEvtDict_Impl();
}
